import json
import re
from collections.abc import Iterator
from typing import Any

from picnic_api.models.rsc import RscPage

ROW_PATTERN = re.compile(r"^([0-9a-f]+):(I?)(.*)$")
SHARED_CHUNK_PREFIXES = ("client-components.", "shared-node_modules_")


def parse_rsc_payload(payload: str) -> RscPage:
    """Parses a React Server Components "flight" payload into its rows.

    The payload holds newline-separated rows of the form `<hex id>:<payload>`. JSON rows go to `rows`, client
    component references (`I[...]`) to `modules`. Hints, text chunks and other non-JSON rows carry no page data
    and are skipped.
    """
    rows = {}
    modules = {}
    for line in payload.split("\n"):
        match = ROW_PATTERN.match(line)
        if not match:
            continue
        row_id, import_marker, value = match.groups()
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            continue
        (modules if import_marker else rows)[row_id] = parsed
    return RscPage(rows=rows, modules=modules)


def find_modules(page: RscPage, module_path: str) -> dict[str, list[Any]]:
    """The client component references (`[path, chunks, export]`) whose path ends with `module_path`, by row id."""
    return {
        module_id: reference
        for module_id, reference in page.modules.items()
        if isinstance(reference, list) and reference and str(reference[0]).endswith(module_path)
    }


def iter_elements(node: Any) -> Iterator[list[Any]]:
    """Yields every React element (`["$", type, key, props]`) in a JSON tree, in document order."""
    if isinstance(node, list):
        if len(node) == 4 and node[0] == "$":
            yield node
        for item in node:
            yield from iter_elements(node=item)
    elif isinstance(node, dict):
        for value in node.values():
            yield from iter_elements(node=value)


def find_element_props(page: RscPage, module_path: str) -> list[dict[str, Any]]:
    """Returns the props of every element rendering the client component whose path ends with `module_path`."""
    types = {f"$L{module_id}" for module_id in find_modules(page=page, module_path=module_path)}
    return [element[3] for element in iter_elements(node=list(page.rows.values())) if element[1] in types]


def module_chunks(page: RscPage, module_path: str) -> list[str]:
    """The page specific client chunks of the component whose path ends with `module_path`.

    Shared container and node_modules chunks hold framework and design system code, never page actions.
    """
    return list(
        dict.fromkeys(
            chunk
            for reference in find_modules(page=page, module_path=module_path).values()
            for chunk in reference[1]
            if not chunk.startswith(SHARED_CHUNK_PREFIXES)
        )
    )
