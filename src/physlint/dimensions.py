from __future__ import annotations

from dataclasses import dataclass

_BASES = ("L", "M", "T", "I", "Θ", "N", "J")
_SYMBOLS = {"L": "m", "M": "kg", "T": "s", "I": "A", "Θ": "K", "N": "mol", "J": "cd"}


def _dim(L=0, M=0, T=0, I=0, Θ=0, N=0, J=0) -> tuple[int, ...]:
    return (L, M, T, I, Θ, N, J)


@dataclass(frozen=True)
class Unit:
    dims: tuple[int, ...]
    scale: float = 1.0

    def __post_init__(self) -> None:
        if len(self.dims) != 7:
            raise ValueError(f"dims must have length 7, got {len(self.dims)}")

    def __mul__(self, other: Unit) -> Unit:
        if not isinstance(other, Unit):
            return NotImplemented
        return Unit(
            tuple(a + b for a, b in zip(self.dims, other.dims)),
            self.scale * other.scale,
        )

    def __truediv__(self, other: Unit) -> Unit:
        if not isinstance(other, Unit):
            return NotImplemented
        return Unit(
            tuple(a - b for a, b in zip(self.dims, other.dims)),
            self.scale / other.scale,
        )

    def __pow__(self, n: int) -> Unit:
        return Unit(tuple(d * n for d in self.dims), self.scale**n)

    def compatible_dims(self, other: Unit) -> bool:
        return self.dims == other.dims

    def compatible(self, other: Unit) -> bool:
        return self.dims == other.dims and self.scale == other.scale


DIMENSIONLESS = Unit(_dim(), 1.0)
UNKNOWN = None


def dims_to_str(unit: Unit) -> str:
    """Format a Unit as a human-readable string (e.g. m/s, kg*m/s^2)."""
    if unit.dims == DIMENSIONLESS.dims:
        return "dimensionless"

    num: list[str] = []
    den: list[str] = []

    for i, exp in enumerate(unit.dims):
        if exp == 0:
            continue
        sym = _SYMBOLS[_BASES[i]]
        bucket = num if exp > 0 else den
        e = abs(exp)
        bucket.append(sym if e == 1 else f"{sym}^{e}")

    top = "*".join(num) if num else "1"
    if not den:
        return top
    bot = "*".join(den)
    if len(den) > 1:
        bot = f"({bot})"
    return f"{top}/{bot}"
