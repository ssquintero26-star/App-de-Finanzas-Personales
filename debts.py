"""Servicios de lógica de negocio para el módulo de deudas."""

from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Case, F, IntegerField, Value, When
from django.utils import timezone

from core.services.payment_queue import (
    DEFAULT_MAX_LEVEL,
    DEFAULT_PRIORITY_THRESHOLDS,
)


def apply_transaction_to_debt(transaction):
    """Actualiza los montos de la deuda asociada a una transacción recién creada/guardada.

    - income → aumenta monto_requerido (el usuario recibió más dinero prestado).
    - expense → aumenta monto_pagado (el usuario abonó a la deuda).
    - transfer → no-op.
    """
    debt = transaction.debt
    if debt is None:
        return

    if transaction.transaction_type == "income":
        debt.monto_requerido += transaction.amount
    elif transaction.transaction_type == "expense":
        debt.monto_pagado += transaction.amount
    else:
        return

    debt.save(update_fields=["monto_requerido", "monto_pagado", "updated_at"])


def revert_transaction_from_debt(transaction):
    """Revierte el efecto de una transacción sobre su deuda (para update/delete)."""
    debt = transaction.debt
    if debt is None:
        return

    if transaction.transaction_type == "income":
        debt.monto_requerido -= transaction.amount
        debt.monto_requerido = max(debt.monto_requerido, Decimal("0.00"))
    elif transaction.transaction_type == "expense":
        debt.monto_pagado -= transaction.amount
        debt.monto_pagado = max(debt.monto_pagado, Decimal("0.00"))
    else:
        return

    debt.save(update_fields=["monto_requerido", "monto_pagado", "updated_at"])


def validate_expense_against_debt(debt, amount):
    """Lanza ValidationError si el monto del gasto supera el saldo pendiente de la deuda."""
    if amount > debt.monto_pendiente:
        raise ValidationError(
            f"El monto del gasto (${amount:,.2f}) supera el saldo pendiente "
            f"de la deuda (${debt.monto_pendiente:,.2f})."
        )


def get_debt_transaction_history(debt):
    """Retorna el queryset de transacciones asociadas a una deuda, ordenadas por fecha."""
    return debt.transactions.select_related("account", "category").order_by("-date")


def order_debts_by_priority(queryset, today: date | None = None):
    """Ordena un queryset de `Debt` por urgencia, resuelto en la base de datos.

    1. Estado: con saldo (pendiente o vencida) primero; pagadas al final.
    2. Nivel de prioridad (1 = más urgente ... 5), con los mismos umbrales que `priority_from_due_date`.
    3. Fecha límite: la que vence primero va primero.
    4. `pk` como desempate.
    """
    today = today or timezone.localdate()
    whens = [
        When(fecha_limite__lte=today + timedelta(days=max_days), then=Value(level))
        for max_days, level in DEFAULT_PRIORITY_THRESHOLDS
    ]
    return (
        queryset.annotate(
            _sin_saldo=Case(
                When(monto_pagado__gte=F("monto_requerido"), then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            _nivel=Case(
                When(monto_pagado__gte=F("monto_requerido"), then=Value(0)),
                *whens,
                default=Value(DEFAULT_MAX_LEVEL),
                output_field=IntegerField(),
            ),
        )
        .order_by("_sin_saldo", "_nivel", "fecha_limite", "pk")
    )