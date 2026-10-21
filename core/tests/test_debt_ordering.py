from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from core.models import Debt
from core.services.debts import order_debts_by_priority
from core.tests.factories import DebtFactory, UserFactory


def mk(user, nombre, dias, pagado="0.00", requerido="1000.00"):
    today = timezone.localdate()
    return DebtFactory(
        user=user,
        nombre=nombre,
        fecha_limite=today + timedelta(days=dias),
        monto_pagado=Decimal(pagado),
        monto_requerido=Decimal(requerido),
    )


@pytest.mark.django_db
def test_orden_estado_prioridad_fecha():
    u = UserFactory()
    today = timezone.localdate()
    mk(u, "pagada_urgente", 0, pagado="1000.00")
    mk(u, "nivel3_b", 20)
    mk(u, "nivel3_a", 10)
    mk(u, "nivel2", 5)
    mk(u, "vencida", -3)
    mk(u, "nivel1_hoy", 0)
    mk(u, "nivel5", 200)
    mk(u, "pagada_vieja", -10, pagado="1000.00")

    qs = order_debts_by_priority(Debt.objects.filter(user=u), today=today)
    assert [d.nombre for d in qs] == [
        "vencida",      # nivel 1, fecha más antigua
        "nivel1_hoy",   # nivel 1
        "nivel2",
        "nivel3_a",     # nivel 3, vence antes
        "nivel3_b",
        "nivel5",
        "pagada_vieja",  # pagadas al final, por fecha
        "pagada_urgente",
    ]