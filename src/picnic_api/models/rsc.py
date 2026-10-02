"""Models for pages served as a React Server Components (RSC) "flight" payload (`text/x-component`).

Picnic serves some pages in this format to newer app versions, depending on the `x-picnic-agent` header.
React elements in the rows are tuples of the form `["$", type, key, props]`; the page data lives in the props.
"""

from typing import Any, Literal

from pydantic import Field

from picnic_api.models.common import PicnicModel

type PageFormat = Literal["fusion", "rsc"]


class RscPage(PicnicModel):
    """A page served as an RSC payload, split into its rows.

    `rows` holds the JSON rows keyed by hex row id (row "0" is the root). `modules` holds the client component
    references (`I[...]` rows); an element type like "$L8" points to `modules["8"]`.
    """

    rows: dict[str, Any] = Field(default_factory=dict)
    modules: dict[str, Any] = Field(default_factory=dict)
