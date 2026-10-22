"""Reglas compartidas para la eliminación de transacciones."""

from copy import copy

from django.core.exceptions import PermissionDenied
from django.db import transaction as db_transaction

from core.models import Debt, Goal, Transaction, User
from core.services.debts import revert_transaction_from_debt
from core.services.goals import revert_transaction_from_goal
from core.services.transaction_stack import TransactionStack


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


def build_transaction_stack(user):
    """Reconstruye la pila del usuario desde la BD en orden de inserción.

    El ID es inmutable y conserva el orden de registro, incluso para datos
    anteriores a la restauración de created_at. La fecha contable no interviene.
    La BD conserva los elementos entre peticiones; no hay una pila global.
    """
    stack = TransactionStack()
    transaction_ids = (
        Transaction.objects.filter(user=user)
        .order_by("pk")
        .values_list("pk", flat=True)
    )
    for transaction_id in transaction_ids.iterator():
        stack.push(transaction_id)
    return stack


def get_latest_transaction_id(user):
    """Consulta el tope sin desapilarlo."""
    stack = build_transaction_stack(user)
    return None if stack.is_empty() else stack.peek()


def validate_latest_transaction(transaction):
    """Impide eliminar un elemento que no esté en el tope de la pila."""
    if transaction.pk != get_latest_transaction_id(transaction.user):
        raise PermissionDenied(
            "Solo se puede eliminar la última transacción registrada."
        )


@db_transaction.atomic
def delete_transaction(transaction):
    """Desapila y elimina el tope, revirtiendo sus efectos de forma atómica."""
    from core.services.shared_expenses import revert_shared_expense_payment_transaction

    # Las altas también bloquean esta fila: un push no puede intercalarse
    # entre la comprobación del tope y su eliminación.
    User.objects.select_for_update().only("pk").get(pk=transaction.user_id)
    stack = build_transaction_stack(transaction.user)
    if stack.is_empty() or stack.peek() != transaction.pk:
        raise PermissionDenied(
            "Solo se puede eliminar la última transacción registrada."
        )
    transaction_id = stack.pop()
    current = Transaction.objects.select_related("debt", "goal").get(
        pk=transaction_id, user_id=transaction.user_id
    )
    revert_transaction_from_debt(current)
    revert_transaction_from_goal(current)
    revert_shared_expense_payment_transaction(current)
    current.delete()
