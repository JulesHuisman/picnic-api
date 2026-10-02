import json
import re

from picnic_api.models.rsc import RscPage

ROW_PATTERN = re.compile(r"^([0-9a-f]+):(I?)(.*)$")


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
