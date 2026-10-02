from collections.abc import Iterator
from typing import Any


def iter_objects(node: Any) -> Iterator[dict[str, Any]]:
    """Yields every object in a JSON tree in document order (pre-order, depth first)."""
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            yield current
            stack.extend(reversed(current.values()))
        elif isinstance(current, list):
            stack.extend(reversed(current))


def find_all(node: Any, key: str) -> list[Any]:
    """Returns the values of `key` anywhere in a JSON tree, in document order (JSONPath `$..key`)."""
    return [obj[key] for obj in iter_objects(node=node) if key in obj]
