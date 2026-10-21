"""Cola con prioridad de pagos pendientes, implementada con `heapq`.

Prioridades: 1 = más urgente, 5 = menos urgente, derivadas de la fecha
límite de cada pago. `heapq` es un min-heap, así que el nivel 1 (menor
clave) sale primero, que es justo lo que queremos.

La cola es en memoria: se reconstruye en cada request desde la BD con
`build_payment_queue(user)`. No se persiste.
"""

import heapq
import itertools
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Iterator

from django.db import models
from django.utils import timezone

# ---------------------------------------------------------------------------
# Mapeo fecha -> nivel de prioridad
# ---------------------------------------------------------------------------

DEFAULT_PRIORITY_THRESHOLDS = (
    (0, 1),    # vencida o vence hoy -> nivel 1
    (7, 2),    # 1..7 días -> nivel 2
    (30, 3),   # 8..30 días -> nivel 3
    (90, 4),   # 31..90 días -> nivel 4
)
DEFAULT_MAX_LEVEL = 5  # más de 90 días -> nivel 5


def priority_from_due_date(
    due_date: date,
    today: date | None = None,
    thresholds=DEFAULT_PRIORITY_THRESHOLDS,
    max_level: int = DEFAULT_MAX_LEVEL,
) -> int:
    """Devuelve 1 (más urgente) a `max_level` (menos urgente) según los
    días que falten para `due_date` respecto a `today`."""
    today = today or timezone.localdate()
    days_left = (due_date - today).days
    for max_days, level in thresholds:
        if days_left <= max_days:
            return level
    return max_level


# ---------------------------------------------------------------------------
# Elemento y cola con prioridad
# ---------------------------------------------------------------------------

@dataclass
class PaymentItem:
    """Elemento de la cola de pagos pendientes."""
    priority: int                 # 1..5 (1 = más urgente)
    due_date: date                # fecha límite del pago
    id: int                       # id del registro origen
    kind: str                     # "debt" | "shared_expense"
    description: str
    amount_pending: Decimal
    payload: Any = field(repr=False, compare=False)  # modelo original


class PaymentPriorityQueue:
    """Cola con prioridad (min-heap) de pagos pendientes.

    - push:  O(log n)
    - pop:   O(log n), devuelve el más urgente
    - peek:  O(1)
    - to_list / iter: O(n log n), ordenados sin destruir la cola

    El desempate entre elementos de igual prioridad y misma fecha es FIFO
    (orden de inserción), gracias al contador monotónico `itertools.count()`.
    """

    def __init__(self):
        self._heap: list[tuple] = []
        self._counter = itertools.count()

    def push(self, item: PaymentItem) -> None:
        if not (1 <= item.priority <= 5):
            raise ValueError(
                f"priority debe estar entre 1 y 5, recibido {item.priority}"
            )
        heapq.heappush(
            self._heap,
            (item.priority, item.due_date, next(self._counter), item),
        )

    def pop(self) -> PaymentItem:
        if not self._heap:
            raise IndexError("pop from empty PaymentPriorityQueue")
        return heapq.heappop(self._heap)[3]

    def peek(self) -> PaymentItem:
        if not self._heap:
            raise IndexError("peek from empty PaymentPriorityQueue")
        return self._heap[0][3]

    def to_list(self) -> list[PaymentItem]:
        return [entry[3] for entry in sorted(self._heap)]

    def is_empty(self) -> bool:
        return not self._heap

    def __len__(self) -> int:
        return len(self._heap)

    def __iter__(self) -> Iterator[PaymentItem]:
        return iter(self.to_list())


# ---------------------------------------------------------------------------
# Adaptador BD -> cola
# ---------------------------------------------------------------------------

def build_debt_items(user, today: date | None = None) -> list[PaymentItem]:
    from core.models import Debt

    today = today or timezone.localdate()
    items = []
    debts = Debt.objects.filter(
        user=user, monto_pagado__lt=models.F("monto_requerido")
    )
    for debt in debts:
        items.append(PaymentItem(
            priority=priority_from_due_date(debt.fecha_limite, today),
            due_date=debt.fecha_limite,
            id=debt.pk,
            kind="debt",
            description=f"Deuda: {debt.nombre} ({debt.prestamista})",
            amount_pending=debt.monto_pendiente,
            payload=debt,
        ))
    return items


def build_owner_shared_expense_items(
    user, today: date | None = None
) -> list[PaymentItem]:
    """Participaciones del DUEÑO con saldo pendiente (lo que él debe a
    contactos que pagaron gastos compartidos)."""
    from core.models import SharedExpenseParticipant

    today = today or timezone.localdate()
    items = []
    qs = SharedExpenseParticipant.objects.filter(
        shared_expense__user=user,
        is_owner=True,
        amount_paid__lt=models.F("amount_assigned"),
    ).select_related("shared_expense")
    for p in qs:
        due = p.shared_expense.date
        items.append(PaymentItem(
            priority=priority_from_due_date(due, today),
            due_date=due,
            id=p.pk,
            kind="shared_expense",
            description=f"Gasto compartido: {p.shared_expense.name}",
            amount_pending=p.amount_pending,
            payload=p,
        ))
    return items


def build_payment_queue(user, today: date | None = None) -> PaymentPriorityQueue:
    """Construye la cola con todos los pagos pendientes del usuario."""
    queue = PaymentPriorityQueue()
    for item in build_debt_items(user, today):
        queue.push(item)
    for item in build_owner_shared_expense_items(user, today):
        queue.push(item)
    return queue
