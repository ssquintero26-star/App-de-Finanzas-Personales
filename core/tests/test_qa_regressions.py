from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import Contact, Goal
from core.services.csv_io import import_transactions_csv
from core.services.goals import apply_transaction_to_goal
from core.services.shared_expenses import (
    build_participant_specs,
    create_shared_expense,
    register_shared_expense_payment,
)
from core.tests.factories import AccountFactory, TransactionFactory, UserFactory


@pytest.mark.django_db
def test_stale_payment_cannot_exceed_remaining_balance():
    account = AccountFactory()
    contact = Contact.objects.create(user=account.user, contact=UserFactory())
    specs = build_participant_specs(True, [contact])
    expense = create_shared_expense(
        user=account.user, name="Pago concurrente", description="", account=account,
        category=None, date="2026-10-01", total_amount=Decimal("100.00"),
        participant_specs=specs, payer_spec=specs[0],
    )
    participant = expense.participants.get(is_owner=False)
    register_shared_expense_payment(
        participant=participant, amount=Decimal("40.00"),
        date="2026-10-02", account=account,
    )
    with pytest.raises(ValidationError):
        register_shared_expense_payment(
            participant=participant, amount=Decimal("20.00"),
            date="2026-10-02", account=account,
        )
    assert participant.payments.count() == 1
    api = APIClient()
    api.force_authenticate(account.user)
    response = api.post(f"/api/shared-expenses/{expense.pk}/register-payment/", {
        "participant": participant.pk, "amount": "20.00",
        "date": "2026-10-02", "account": account.pk,
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_goal_validation_returns_400_and_edit_does_not_double_count(client):
    account = AccountFactory()
    goal = Goal.objects.create(
        user=account.user, nombre="Meta", monto_requerido=Decimal("100.00"),
        monto_abonado=0, fecha_limite="2026-12-31",
    )
    tx = TransactionFactory(
        user=account.user, account=account, goal=goal,
        transaction_type="income", amount=Decimal("100.00"), category=None,
    )
    apply_transaction_to_goal(tx)
    api = APIClient()
    api.force_authenticate(account.user)
    url = reverse("transaction-detail", args=[tx.pk])
    response = api.patch(url, {"description": "Meta completada"})
    assert response.status_code == 200
    goal.refresh_from_db()
    assert goal.monto_abonado == Decimal("100.00")
    assert api.patch(url, {"amount": "101.00"}).status_code == 400
    client.force_login(account.user)
    response = client.post(reverse("core:transaction_update", args=[tx.pk]), {
        "account": account.pk, "transaction_type": "income", "amount": "100.00",
        "description": "Descripción corregida", "date": "2026-10-01",
        "asociar_a": f"goal:{goal.pk}",
    })
    assert response.status_code == 302
    goal.refresh_from_db()
    assert goal.monto_abonado == Decimal("100.00")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "amount", ["-1", "0", "NaN", "Infinity", "1.001", "1000000000000"]
)
def test_csv_rejects_invalid_amounts_without_creating_rows(amount):
    account = AccountFactory(name="Cuenta")
    content = (
        "date,account,amount,description,transaction_type\n"
        f"2026-10-01,Cuenta,{amount},Inválido,expense\n"
    )
    result = import_transactions_csv(account.user, content)
    assert result["created"] == 0
    assert result["errors"]
    assert account.transactions.count() == 0
