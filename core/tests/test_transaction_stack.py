from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Contact, SharedExpense, Transaction
from core.services.shared_expenses import build_participant_specs, create_shared_expense
from core.services.transaction_stack import TransactionStack
from core.services.transactions import (
    build_transaction_stack,
    delete_transaction,
    get_latest_transaction_id,
)
from core.tests.factories import (
    AccountFactory,
    DebtFactory,
    TransactionFactory,
    UserFactory,
)


def test_stack_push_pop_is_lifo():
    stack = TransactionStack()
    assert stack.is_empty()
    for transaction_id in (10, 20, 30):
        stack.push(transaction_id)
    assert len(stack) == 3
    assert stack.peek() == 30
    assert len(stack) == 3
    assert [stack.pop(), stack.pop(), stack.pop()] == [30, 20, 10]
    assert stack.is_empty()
    assert len(stack) == 0
    stack.push(40)
    assert stack.pop() == 40


@pytest.mark.parametrize("operation", ["pop", "peek"])
def test_empty_stack_raises_without_changing_state(operation):
    stack = TransactionStack()
    with pytest.raises(IndexError):
        getattr(stack, operation)()
    assert stack.is_empty()
    assert len(stack) == 0


@pytest.mark.django_db
def test_stack_rebuilds_per_user_and_ignores_editable_dates():
    first = TransactionFactory(date="2026-10-01")
    second = TransactionFactory(user=first.user, date="2025-01-01")
    TransactionFactory()  # La pila de otro usuario no se mezcla.
    first.date = "2030-01-01"
    first.created_at = timezone.now() + timedelta(days=1)
    first.save()
    stack = build_transaction_stack(first.user)
    assert stack.pop() == second.pk
    assert stack.pop() == first.pk
    # Desapilar una copia de lectura no modifica la persistencia.
    assert get_latest_transaction_id(first.user) == second.pk
    delete_transaction(second)
    assert get_latest_transaction_id(first.user) == first.pk
    delete_transaction(first)
    assert get_latest_transaction_id(first.user) is None


@pytest.mark.django_db
@pytest.mark.parametrize("surface", ["web", "api"])
def test_new_registration_invalidates_an_old_delete_confirmation(client, surface):
    first = TransactionFactory(date="2026-10-10")
    client.force_login(first.user)
    confirmation_url = reverse("core:transaction_delete", args=[first.pk])
    assert client.get(confirmation_url).status_code == 200
    latest = TransactionFactory(user=first.user, date="2020-01-01")
    if surface == "web":
        response = client.post(reverse("core:transaction_delete", args=[first.pk]))
    else:
        api = APIClient()
        api.force_authenticate(first.user)
        response = api.delete(reverse("transaction-detail", args=[first.pk]))
    assert response.status_code == 403
    assert Transaction.objects.filter(pk__in=[first.pk, latest.pk]).count() == 2


@pytest.mark.django_db
def test_failed_delete_rolls_back_balances_and_retains_stack_top(monkeypatch):
    tx = TransactionFactory(amount=Decimal("50.00"))
    debt = DebtFactory(user=tx.user, monto_pagado=Decimal("50.00"))
    tx.debt = debt
    tx.save()

    def fail(_transaction):
        raise RuntimeError("Fallo simulado después de revertir la deuda")

    monkeypatch.setattr("core.services.transactions.revert_transaction_from_goal", fail)
    with pytest.raises(RuntimeError):
        delete_transaction(tx)
    debt.refresh_from_db()
    assert debt.monto_pagado == Decimal("50.00")
    assert Transaction.objects.filter(pk=tx.pk).exists()
    assert get_latest_transaction_id(tx.user) == tx.pk


@pytest.mark.django_db
def test_cannot_pop_an_older_transaction_directly():
    older = TransactionFactory()
    latest = TransactionFactory(user=older.user)
    with pytest.raises(PermissionDenied):
        delete_transaction(older)
    assert get_latest_transaction_id(older.user) == latest.pk


@pytest.mark.django_db
@pytest.mark.parametrize("surface", ["web", "api"])
def test_shared_expense_cannot_bypass_stack(client, surface):
    account = AccountFactory()
    contact = Contact.objects.create(user=account.user, contact=UserFactory())
    specs = build_participant_specs(True, [contact])
    expense = create_shared_expense(
        user=account.user, account=account, category=None, name="Pila compartida",
        description="", date="2026-10-01", total_amount=Decimal("100.00"),
        participant_specs=specs, payer_spec=specs[0],
    )
    newer = TransactionFactory(user=account.user, date="2020-01-01")
    expense_pk, transaction_pk = expense.pk, expense.transaction_id
    if surface == "web":
        client.force_login(account.user)
        url = reverse("core:shared_expense_delete", args=[expense_pk])
        assert client.get(url).status_code == 403

        def remove():
            return client.post(url)
    else:
        api = APIClient()
        api.force_authenticate(account.user)
        url = reverse("shared-expense-detail", args=[expense_pk])

        def remove():
            return api.delete(url)
    assert remove().status_code == 403
    assert SharedExpense.objects.filter(pk=expense_pk).exists()
    assert Transaction.objects.filter(pk=transaction_pk).exists()
    delete_transaction(newer)
    assert remove().status_code == (302 if surface == "web" else 204)
    assert not SharedExpense.objects.filter(pk=expense_pk).exists()
    assert not Transaction.objects.filter(pk=transaction_pk).exists()
