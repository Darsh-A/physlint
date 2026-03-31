from __future__ import annotations

from physlint.dimensions import Unit, _dim

BASE: dict[str, Unit] = {
    "m": Unit(_dim(L=1)),
    "kg": Unit(_dim(M=1)),
    "s": Unit(_dim(T=1)),
    "A": Unit(_dim(I=1)),
    "K": Unit(_dim(Θ=1)),
    "mol": Unit(_dim(N=1)),
    "cd": Unit(_dim(J=1)),
}

DERIVED: dict[str, str] = {
    "Hz": "1/s",
    "N": "kg*m/s^2",
    "Pa": "N/m^2",
    "J": "N*m",
    "W": "J/s",
    "V": "W/A",
    "Ω": "V/A", "Ohm": "V/A", "ohm": "V/A",
    "C": "A*s",
    "F": "C/V",
    "T": "kg/(A*s^2)",
    "Wb": "V*s",
    "lm": "cd",
    "lx": "lm/m^2",
    "Gy": "J/kg",
    "kat": "mol/s",
}

PREFIXES: dict[str, float] = {
    "Y": 1e24, "Z": 1e21, "E": 1e18, "P": 1e15, "T": 1e12,
    "G": 1e9, "M": 1e6, "k": 1e3, "h": 1e2, "da": 1e1,
    "d": 1e-1, "c": 1e-2, "m": 1e-3,
    "μ": 1e-6, "u": 1e-6, "mu": 1e-6,
    "n": 1e-9, "p": 1e-12, "f": 1e-15, "a": 1e-18,
    "z": 1e-21, "y": 1e-24,
}

ALIASES: dict[str, str] = {
    "g": "kg", "L": "m^3", "min": "s", "hr": "s", "day": "s",
    "eV": "J", "bar": "Pa", "atm": "Pa", "cal": "J",
    "Å": "m", "angstrom": "m", "au": "m", "ly": "m",
    "mph": "m/s", "rpm": "1/s",
    "dB": "", "ppm": "", "rad": "", "°": "", "deg": "", "sr": "",
}

_ALIAS_SCALES: dict[str, float] = {
    "g": 1e-3,
    "min": 60.0,
    "hr": 3600.0,
    "day": 86400.0,
    "L": 1e-3,
    "Å": 1e-10,
    "angstrom": 1e-10,
}

_PREFIX_KEYS_SORTED = sorted(PREFIXES, key=len, reverse=True)
_cache: dict[str, Unit | None] = {}


def resolve(name: str, _resolving: set[str] | None = None) -> Unit | None:
    if name in _cache:
        return _cache[name]
    if _resolving is None:
        _resolving = set()
    if name in _resolving:
        return None
    _resolving = _resolving | {name}
    result = _resolve_inner(name, _resolving)
    _cache[name] = result
    return result


def _resolve_inner(name: str, _resolving: set[str]) -> Unit | None:
    if name in BASE:
        return BASE[name]

    if name in DERIVED:
        from physlint.parser import parse_unit
        return parse_unit(DERIVED[name], _resolving=_resolving)

    if name in ALIASES:
        target = ALIASES[name]
        if target == "":
            from physlint.dimensions import DIMENSIONLESS
            result = DIMENSIONLESS
        else:
            from physlint.parser import parse_unit
            result = parse_unit(target, _resolving=_resolving)
        if result is not None and name in _ALIAS_SCALES:
            result = Unit(result.dims, result.scale * _ALIAS_SCALES[name])
        return result

    for prefix in _PREFIX_KEYS_SORTED:
        if name.startswith(prefix) and len(name) > len(prefix):
            base_unit = resolve(name[len(prefix):], _resolving)
            if base_unit is not None:
                return Unit(base_unit.dims, base_unit.scale * PREFIXES[prefix])

    return None
