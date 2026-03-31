from __future__ import annotations

from physlint.dimensions import Unit


class SymbolTable:
    def __init__(self) -> None:
        self._store: dict[str, Unit] = {}

    def set(self, name: str, unit: Unit | None) -> None:
        if unit is not None:
            self._store[name] = unit

    def get(self, name: str) -> Unit | None:
        return self._store.get(name)

    def has(self, name: str) -> bool:
        return name in self._store

    def remove(self, name: str) -> None:
        self._store.pop(name, None)
