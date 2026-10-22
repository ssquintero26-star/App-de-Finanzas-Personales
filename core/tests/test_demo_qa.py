"""Recorrido de la demo y regresiones de las pantallas con pagos compartidos."""

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import Budget, SharedExpense, SharedExpensePayment, Transaction, User
from core.services.reports import get_monthly_income_expense
from core.services.transactions import get_latest_transaction_id


@pytest.mark.django_db
def test_demo_is_repeatable_and_all_screens_and_api_render(client):
    call_command("setup_demo", verbosity=0)
    models = (User, Transaction, Budget, SharedExpensePayment)
    counts = [model.objects.count() for model in models]
    call_command("setup_demo", verbosity=0)
    assert counts == [model.objects.count() for model in models]
    user = User.objects.get(email="demo@fintrack.local")
    assert client.login(username=user.email, password="demo1234")
    chart = get_monthly_income_expense(user)
    assert len(chart["labels"]) == 6
    assert all(value > 0 for value in chart["income"])
    assert all(value > 0 for value in chart["expense"])
    assert set(SharedExpense.objects.filter(user=user).values_list("name", flat=True))
    states = {expense.estado for expense in SharedExpense.objects.filter(user=user)}
    assert states == {"pendiente", "parcial", "completado"}

    routes = ["dashboard", "csv_import", "csv_export", "pdf_report"]
    for resource in (
        "account", "category", "budget", "debt", "goal", "contact", "group",
        "shared_expense", "transaction",
    ):
        routes.extend([f"{resource}_list", f"{resource}_create"])
    for route in routes:
        response = client.get(reverse(f"core:{route}"))
        assert response.status_code == 200, route

    for expense in SharedExpense.objects.filter(user=user):
        for route in (
            "shared_expense_detail", "shared_expense_payment_create",
            "shared_expense_delete",
        ):
            response = client.get(reverse(f"core:{route}", args=[expense.pk]))
            blocked = (
                route == "shared_expense_delete"
                and expense.transaction_id is not None
                and expense.transaction_id != get_latest_transaction_id(user)
            )
            assert response.status_code == (403 if blocked else 200), (route, expense.pk)
    for resource, relation in [
        ("debt", user.debts), ("goal", user.goals), ("contact", user.contacts),
        ("group", user.contact_groups),
    ]:
        for obj in relation.all():
            url = reverse(f"core:{resource}_detail", args=[obj.pk])
            assert client.get(url).status_code == 200

    api = APIClient()
    api.force_authenticate(user)
    for path in (
        "accounts", "categories", "tags", "budgets", "debts", "goals", "contacts",
        "contact-groups", "shared-expenses", "transactions", "dashboard",
    ):
        assert api.get(f"/api/{path}/").status_code == 200, path
    for expense in SharedExpense.objects.filter(user=user):
        url = f"/api/shared-expenses/{expense.pk}/payments/"
        assert api.get(url).status_code == 200
    assert client.post(reverse("core:logout")).status_code == 302
    assert client.get(reverse("core:dashboard")).status_code == 302


@pytest.mark.django_db
def test_anonymous_payment_page_redirects_to_login(client):
    response = client.get(reverse("core:shared_expense_payment_create", args=[1]))
    assert response.status_code == 302
    assert "/login/" in response.url
