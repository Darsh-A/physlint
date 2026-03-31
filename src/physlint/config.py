from __future__ import annotations

import pathlib
from dataclasses import dataclass, field


@dataclass
class Config:
    strict: bool = False
    strict_scale: bool = True
    ignore_prefix: list[str] = field(default_factory=list)
    aliases: dict[str, str] = field(default_factory=dict)
    ignore_rules: list[str] = field(default_factory=list)


def load_config(path: pathlib.Path | None = None) -> Config:
    if path is None:
        path = pathlib.Path.cwd() / "physlint.toml"
    if not path.exists():
        return Config()

    data = _load_toml(path)
    section = data.get("physlint", data)
    return Config(
        strict=section.get("strict", False),
        strict_scale=section.get("strict_scale", True),
        ignore_prefix=section.get("ignore_prefix", []),
        aliases=section.get("aliases", {}),
        ignore_rules=section.get("ignore_rules", []),
    )


def _load_toml(path: pathlib.Path) -> dict:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]
    with open(path, "rb") as f:
        return tomllib.load(f)
