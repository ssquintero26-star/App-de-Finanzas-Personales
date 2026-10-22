"""Reglas compartidas para la eliminación de transacciones."""

from copy import copy

from django.core.exceptions import PermissionDenied

from core.models import Debt, Goal, Transaction


def association_before_transaction(association, previous):
    """Revierte en memoria el aporte anterior para validar una edición."""
    if association is None or previous is None:
        return association
    result = copy(association)
    if isinstance(result, Debt) and previous.debt_id == result.pk:
        if previous.transaction_type == "income":
            result.monto_requerido -= previous.amount
        elif previous.transaction_type == "expense":
            result.monto_pagado -= previous.amount
    elif isinstance(result, Goal) and previous.goal_id == result.pk:
        if previous.transaction_type == "income":
            result.monto_abonado -= previous.amount
        elif previous.transaction_type == "expense":
            result.monto_abonado += previous.amount
    return result


def get_latest_transaction_id(user):
    """Obtiene la primera transacción del historial completo del usuario."""
    return (
        Transaction.objects.filter(user=user)
        .order_by("-date", "-pk")
        .values_list("pk", flat=True)
        .first()
    )


def validate_latest_transaction(transaction):
    """Impide eliminar transacciones anteriores a la última del usuario."""
    if transaction.pk != get_latest_transaction_id(transaction.user):
        raise PermissionDenied("Solo se puede eliminar la última transacción.")
