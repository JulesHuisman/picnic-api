"""Read-only checks against the live Picnic API. Run with `uv run --env-file .env pytest -m integration`."""

import os
from collections.abc import Iterator

import pytest

from picnic_api import PicnicClient, UnexpectedPageFormatError

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(condition=not os.environ.get("PICNIC_AUTH_KEY"), reason="PICNIC_AUTH_KEY is not set"),
]


@pytest.fixture(scope="module")
def live_client() -> Iterator[PicnicClient]:
    with PicnicClient(auth_key=os.environ["PICNIC_AUTH_KEY"]) as client:
        yield client


def test_get_page_returns_a_fusion_page(live_client: PicnicClient) -> None:
    assert live_client.app.get_page(page_id="home_page_root").layout.body


def test_get_page_rejects_rsc_pages(live_client: PicnicClient) -> None:
    with pytest.raises(UnexpectedPageFormatError) as error:
        live_client.app.get_page(page_id="category-tree-root")

    assert (error.value.page_id, error.value.received_format) == ("category-tree-root", "rsc")


def test_get_rsc_page_parses_the_payload(live_client: PicnicClient) -> None:
    page = live_client.app.get_rsc_page(page_id="category-tree-root")

    assert page.rows
    assert page.modules
    assert '"name":"category-tree"' in page.model_dump_json()


def test_get_rsc_page_rejects_fusion_pages(live_client: PicnicClient) -> None:
    with pytest.raises(UnexpectedPageFormatError):
        live_client.app.get_rsc_page(page_id="home_page_root")


def test_search(live_client: PicnicClient) -> None:
    results = live_client.catalog.search(query="Affligem blond")

    assert results
    assert "s1" in results[0].id
    assert "Affligem blond" in (results[0].name or "")


def test_product_details_page(live_client: PicnicClient) -> None:
    assert live_client.catalog.get_product_details_page(product_id="s1001524").layout.id == "product-details-page-root"


@pytest.mark.parametrize(
    argnames=("product_id", "name", "brand", "unit_quantity"),
    argvalues=[
        ("s1001504", "Rode paprika", None, "1 stuk"),
        ("s1139960", "Witte vrije uitloop eieren", "Picnic", "6 stuks"),
        ("s1009498", "Spinazie gewassen", "Picnic", "200 gram"),
    ],
)
def test_product_details(
    live_client: PicnicClient, product_id: str, name: str, brand: str | None, unit_quantity: str
) -> None:
    details = live_client.catalog.get_product_details(product_id=product_id)

    assert (details.id, details.name, details.brand, details.unit_quantity) == (product_id, name, brand, unit_quantity)
