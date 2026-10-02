from typing import Any

import httpx

from picnic_api import PicnicClient
from picnic_api.domains.catalog.helpers import extract_product_details, find_by_id
from picnic_api.models.fusion import FusionPage, PriceRange
from tests.conftest import MockApi

PRODUCT_ID = "s1001524"


def text(markdown: str, **attributes: Any) -> dict[str, Any]:
    return {"type": "RICH_TEXT", "markdown": markdown, **attributes}


def page(body: dict[str, Any], script: dict[str, Any] | None = None) -> FusionPage:
    return FusionPage.model_validate(
        obj={"script": script or {}, "layout": {"id": "product-details-page-root", "header": None, "body": body}}
    )


def full_product_page() -> FusionPage:
    main_container = {
        "id": "product-details-page-root-main-container",
        "pml": {
            "component": {
                "type": "STACK",
                "children": [
                    text("#(#333333)Blond#(#333333)", textType="HEADER1"),
                    text("Affligem", textAttributes={"weight": "REGULAR"}),
                    {
                        "type": "STACK",
                        "children": [text("6 x 300 ml"), {"type": "ICON"}, text("#(#B40117)€4.81/l")],
                    },
                    {"type": "PRICE", "price": 865},
                ],
            }
        },
    }
    accordion = {
        "id": "accordion-list",
        "pml": {
            "component": {
                "type": "ACCORDION",
                "items": [
                    {"header": text("**Ingrediënten**"), "body": {"children": [text("Water"), text("Gerst")]}},
                    "not-an-item",
                ],
            }
        },
    }
    bundles = {
        "id": "product-page-bundles-container",
        "children": [
            {
                "type": "STATE_BOUNDARY",
                "id": "s1001524",
                "child": {"sellingUnit": {"id": "s1001524", "image_id": "img-1", "max_count": 50}, "price": 865},
            },
            {"type": "STATE_BOUNDARY", "id": "s9999999", "child": {"price": 800}},
            {
                "type": "STATE_BOUNDARY",
                "id": "s1001525",
                "child": {"sellingUnit": {"id": "s1001525"}, "price": "n/a"},
            },
        ],
    }
    alternatives = {
        "id": "alternatives-container",
        "children": [
            {
                "sellingUnit": {
                    "id": "s2",
                    "name": "Leffe",
                    "image_id": "img-2",
                    "display_price": 999,
                    "unit_quantity": "6 x 300 ml",
                    "max_count": 50,
                    "deposit": 90,
                }
            },
            {"sellingUnit": {"id": "s3", "name": "No price"}},
        ],
    }
    body = {
        "type": "STATE_BOUNDARY",
        "id": "root",
        "child": {
            "children": [
                main_container,
                {"sellingUnit": {"id": PRODUCT_ID, "max_count": 50, "image_id": "unit-image"}},
                {
                    "id": "product-page-image-gallery-main-image-container",
                    "children": [{"source": {"id": "a"}}, {"source": {"id": "b"}}, {"source": {"id": "a"}}],
                },
                {"id": "description", "children": [text("Goudblond"), text("abdijbier")]},
                {"id": "product-page-highlights", "children": [text("**Fruitig**"), text("__Vol__")]},
                {"id": "product-page-allergies", "children": [text("Bevat"), text("Gluten"), text("Bevat mogelijk")]},
                accordion,
                {"promotion_id": "promo-1", "promotion_label": "1+1 gratis"},
                bundles,
                alternatives,
            ]
        },
    }
    script = {"getCurrentPrice": {"__ep1": {"v1": "not ranges"}, "__ep2": {"v1": [{"price": 800, "from_quantity": 2}]}}}
    return page(body=body, script=script)


def test_extract_product_details_reads_every_section() -> None:
    details = extract_product_details(product_id=PRODUCT_ID, page=full_product_page())

    assert (details.name, details.brand, details.unit_quantity, details.unit_price) == (
        "Blond",
        "Affligem",
        "6 x 300 ml",
        "€4.81/l",
    )
    assert details.display_price == 865
    assert details.max_count == 50
    assert details.image_ids == ["a", "b"]
    assert details.description == "Goudblond\nabdijbier"
    assert details.highlights == ["Fruitig", "Vol"]
    assert details.allergens == ["Gluten"]
    assert [(section.title, section.content) for section in details.info_sections] == [
        ("Ingrediënten", "Water\nGerst"),
        ("", ""),
    ]
    assert details.promotion is not None
    assert (details.promotion.id, details.promotion.label) == ("promo-1", "1+1 gratis")
    assert [(bundle.id, bundle.quantity, bundle.price_per_unit) for bundle in details.bundles] == [
        ("s1001524", 1, 865),
        ("s1001525", 3, 0),
    ]
    assert details.price_ranges == [PriceRange(price=800, from_quantity=2)]
    assert [(product.id, product.deposit) for product in details.similar_products] == [("s2", 90)]


def test_extract_product_details_prefers_selling_unit_data() -> None:
    body = {
        "children": [
            {
                "sellingUnit": {
                    "id": PRODUCT_ID,
                    "max_count": 12,
                    "display_price": 499,
                    "image_id": "unit-image",
                    "price_ranges": [{"price": 450, "from_quantity": 3}],
                }
            },
        ]
    }

    details = extract_product_details(product_id=PRODUCT_ID, page=page(body=body))

    assert details.display_price == 499
    assert details.image_ids == ["unit-image"]
    assert details.price_ranges == [PriceRange(price=450, from_quantity=3)]
    assert (details.name, details.brand, details.unit_quantity, details.unit_price) == ("", None, "", None)
    assert (details.description, details.promotion, details.bundles, details.info_sections) == (None, None, [], [])


def test_extract_product_details_uses_the_bundle_node_price() -> None:
    body = {"children": [{"id": PRODUCT_ID, "child": {"price": 777}}]}

    details = extract_product_details(product_id=PRODUCT_ID, page=page(body=body))

    assert details.display_price == 777
    assert details.max_count == 0
    assert details.image_ids == []
    assert details.price_ranges is None


def test_extract_product_details_falls_back_to_the_price_component() -> None:
    main_container = {
        "id": "product-details-page-root-main-container",
        "pml": {"component": {"children": [{"type": "PRICE", "price": None}, {"type": "PRICE", "price": 349}]}},
    }

    details = extract_product_details(product_id=PRODUCT_ID, page=page(body={"children": [main_container]}))

    assert details.display_price == 349


def test_find_by_id_follows_child_links_only() -> None:
    tree = {"id": "root", "child": {"children": [{"id": "deep"}]}, "other": {"id": "hidden"}}

    assert find_by_id(node=tree, node_id="deep") == {"id": "deep"}
    assert find_by_id(node=tree, node_id="hidden") is None


def test_search_returns_selling_units(client: PicnicClient, api: MockApi) -> None:
    api.queue_json(
        {
            "layout": {
                "body": {
                    "children": [
                        {"sellingUnit": {"id": "s1001524", "name": "Affligem blond", "display_price": 865}},
                        {"child": {"sellingUnit": {"id": "s1001525", "name": "Affligem blond 0.0"}}},
                    ]
                }
            }
        }
    )

    results = client.catalog.search(query="Affligem blond")

    assert [unit.name for unit in results] == ["Affligem blond", "Affligem blond 0.0"]
    assert api.last.url.path.endswith("/pages/search-page-results")
    assert api.last.url.params["search_term"] == "Affligem blond"
    assert "x-picnic-agent" in api.last.headers


def test_get_product_details_fetches_and_parses_the_page(client: PicnicClient, api: MockApi) -> None:
    api.queue_json(full_product_page().raw())

    details = client.catalog.get_product_details(product_id=PRODUCT_ID)

    assert details.name == "Blond"
    assert api.last.url.params["id"] == PRODUCT_ID


def test_images(client: PicnicClient, api: MockApi) -> None:
    api.queue(httpx.Response(status_code=200, content=b"png"), httpx.Response(status_code=200, content=b"png"))

    assert client.catalog.get_image(image_id="abc", size="small") == b"png"
    assert str(api.last.url) == "https://storefront-prod.nl.picnicinternational.com/static/images/abc/small.png"
    assert client.catalog.get_image_as_data_uri(image_id="abc", size="small") == "data:image/png;base64,cG5n"


def test_extract_product_details_finds_a_wrapped_name() -> None:
    main_container = {
        "id": "product-details-page-root-main-container",
        "pml": {"component": {"children": [{"type": "TOUCHABLE", "child": text("Spinazie", textType="HEADER1")}]}},
    }

    details = extract_product_details(product_id=PRODUCT_ID, page=page(body={"children": [main_container]}))

    assert details.name == "Spinazie"
