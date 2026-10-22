"""La eliminación solo está disponible para la última transacción del usuario."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import Transaction
from core.tests.factories import TransactionFactory


@pytest.fixture
def history(db, client):
    older = TransactionFactory(date="2026-01-01")
    latest = TransactionFactory(user=older.user, date="2026-02-01")
    client.force_login(older.user)
    return older, latest


@pytest.mark.django_db
def test_list_only_offers_latest_deletion(client, history):
    older, latest = history
    TransactionFactory(date="2026-03-01")  # Otro usuario no afecta la regla.
    response = client.get(reverse("core:transaction_list"))
    html = response.content.decode()
    assert reverse("core:transaction_delete", args=[latest.pk]) in html
    assert reverse("core:transaction_delete", args=[older.pk]) not in html

    response = client.get(reverse("core:transaction_list"), {"date_to": "2026-01-31"})
    assert reverse("core:transaction_delete", args=[older.pk]) not in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["get", "post"])
def test_web_blocks_older_transaction(client, history, method):
    older, latest = history
    response = getattr(client, method)(reverse("core:transaction_delete", args=[older.pk]))
    assert response.status_code == 403
    assert Transaction.objects.filter(pk__in=[older.pk, latest.pk]).count() == 2


@pytest.mark.django_db
def test_deleting_latest_unlocks_previous(client, history):
    older, latest = history
    assert client.get(reverse("core:transaction_delete", args=[latest.pk])).status_code == 200
    assert client.post(reverse("core:transaction_delete", args=[latest.pk])).status_code == 302
    assert not Transaction.objects.filter(pk=latest.pk).exists()
    assert client.post(reverse("core:transaction_delete", args=[older.pk])).status_code == 302
    assert not Transaction.objects.filter(pk=older.pk).exists()


@pytest.mark.django_db
def test_api_enforces_same_deletion_rule(history):
    older, latest = history
    api = APIClient()
    api.force_authenticate(older.user)
    assert api.delete(reverse("transaction-detail", args=[older.pk])).status_code == 403
    assert Transaction.objects.filter(pk=older.pk).exists()
    assert api.delete(reverse("transaction-detail", args=[latest.pk])).status_code == 204
    assert api.delete(reverse("transaction-detail", args=[older.pk])).status_code == 204


@pytest.mark.django_db
def test_stack_uses_registration_order_even_for_backdated_entries(client, history):
    older, latest = history
    same_date = TransactionFactory(user=older.user, date=latest.date)
    backdated = TransactionFactory(user=older.user, date="2025-12-01")
    assert client.post(reverse("core:transaction_delete", args=[latest.pk])).status_code == 403
    assert client.post(reverse("core:transaction_delete", args=[same_date.pk])).status_code == 403
    response = client.get(reverse("core:transaction_list"))
    assert response.context["transactions"][0].pk == backdated.pk
    assert client.post(reverse("core:transaction_delete", args=[backdated.pk])).status_code == 302
    assert client.post(reverse("core:transaction_delete", args=[same_date.pk])).status_code == 302


@pytest.mark.django_db
def test_other_users_transaction_is_inaccessible(client, history):
    other = TransactionFactory()
    assert client.post(reverse("core:transaction_delete", args=[other.pk])).status_code == 404
    assert Transaction.objects.filter(pk=other.pk).exists()
