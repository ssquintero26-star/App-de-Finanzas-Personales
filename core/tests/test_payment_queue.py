from datetime import date, timedelta
from decimal import Decimal

import pytest

from core.services.payment_queue import (
    PaymentItem,
    PaymentPriorityQueue,
    priority_from_due_date,
)


def make_item(priority, due, id, kind="debt"):
    return PaymentItem(
        priority=priority, due_date=due, id=id, kind=kind,
        description=f"item {id}", amount_pending=Decimal("100.00"),
        payload=None,
    )


def test_priority_boundaries():
    today = date(2026, 1, 1)
    assert priority_from_due_date(today - timedelta(days=1), today) == 1
    assert priority_from_due_date(today, today) == 1
    assert priority_from_due_date(today + timedelta(days=1), today) == 2
    assert priority_from_due_date(today + timedelta(days=7), today) == 2
    assert priority_from_due_date(today + timedelta(days=8), today) == 3
    assert priority_from_due_date(today + timedelta(days=30), today) == 3
    assert priority_from_due_date(today + timedelta(days=31), today) == 4
    assert priority_from_due_date(today + timedelta(days=90), today) == 4
    assert priority_from_due_date(today + timedelta(days=91), today) == 5


def test_pop_returns_most_urgent_first():
    q = PaymentPriorityQueue()
    q.push(make_item(3, date(2026, 1, 10), 1))
    q.push(make_item(1, date(2026, 1, 5), 2))
    q.push(make_item(2, date(2026, 1, 7), 3))
    assert [q.pop().id for _ in range(3)] == [2, 3, 1]


def test_tiebreaks_by_due_date():
    q = PaymentPriorityQueue()
    q.push(make_item(2, date(2026, 1, 9), 1))
    q.push(make_item(2, date(2026, 1, 7), 2))
    assert [q.pop().id for _ in range(2)] == [2, 1]


def test_fifo_for_equal_priority_and_date():
    q = PaymentPriorityQueue()
    q.push(make_item(2, date(2026, 1, 7), 1))
    q.push(make_item(2, date(2026, 1, 7), 2))
    q.push(make_item(2, date(2026, 1, 7), 3))
    assert [q.pop().id for _ in range(3)] == [1, 2, 3]


def test_to_list_does_not_destroy():
    q = PaymentPriorityQueue()
    q.push(make_item(2, date(2026, 1, 7), 1))
    q.push(make_item(1, date(2026, 1, 5), 2))
    assert [i.id for i in q.to_list()] == [2, 1]
    assert len(q) == 2
    assert q.pop().id == 2


def test_peek():
    q = PaymentPriorityQueue()
    q.push(make_item(3, date(2026, 1, 10), 1))
    q.push(make_item(1, date(2026, 1, 5), 2))
    assert q.peek().id == 2
    assert len(q) == 2


def test_invalid_priority_raises():
    q = PaymentPriorityQueue()
    with pytest.raises(ValueError):
        q.push(make_item(0, date(2026, 1, 5), 1))
    with pytest.raises(ValueError):
        q.push(make_item(6, date(2026, 1, 5), 1))


def test_pop_empty_raises():
    q = PaymentPriorityQueue()
    with pytest.raises(IndexError):
        q.pop()
