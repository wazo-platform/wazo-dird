from typing import Any


def projection(m: dict[str, Any], keys: list[str], default=None) -> dict[str, Any]:
    return {k: m.get(k, default) for k in keys}
