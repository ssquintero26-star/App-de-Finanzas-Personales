"""Pila enlazada LIFO de identificadores de transacciones."""

from dataclasses import dataclass


@dataclass(slots=True)
class _Node:
    transaction_id: int
    previous: "_Node | None" = None


class TransactionStack:
    """Pila LIFO con push, pop y peek O(1), sin ordenar sus elementos."""

    def __init__(self):
        self._top: _Node | None = None
        self._size = 0

    def push(self, transaction_id: int) -> None:
        self._top = _Node(transaction_id, self._top)
        self._size += 1

    def peek(self) -> int:
        if self._top is None:
            raise IndexError("La pila de transacciones está vacía.")
        return self._top.transaction_id

    def pop(self) -> int:
        transaction_id = self.peek()
        self._top = self._top.previous
        self._size -= 1
        return transaction_id

    def is_empty(self) -> bool:
        return self._top is None

    def __len__(self) -> int:
        return self._size
