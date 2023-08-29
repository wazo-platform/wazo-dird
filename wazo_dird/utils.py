from typing import Mapping, TypeVar

K = TypeVar("K")
V = TypeVar("V")


def projection(m: Mapping[K, V], keys: list[K], default=None) -> dict[K, V]:
    """
    Extract a subset of key:value pairs from a mapping into a new dictionary.
    >>> projection({'a': 1, 'b': 2}, ['a'])
    {'a': 1}

    """
    return {k: m.get(k, default) for k in keys}
