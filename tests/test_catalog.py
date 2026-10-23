import json
from typing import Any

import httpx
import pytest

from picnic_api import PicnicClient, PicnicError
from picnic_api.domains.catalog.helpers import extract_product_details, find_by_id
from picnic_api.models.fusion import FusionPage, PriceRange, SellingUnit
from tests import samples
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


async def test_find_by_id_follows_child_links_only() -> None:
    tree = {"id": "root", "child": {"children": [{"id": "deep"}]}, "other": {"id": "hidden"}}

    assert find_by_id(node=tree, node_id="deep") == {"id": "deep"}
    assert find_by_id(node=tree, node_id="hidden") is None


def rsc(*rows: str) -> httpx.Response:
    return httpx.Response(status_code=200, text="\n".join(rows), headers={"content-type": "text/x-component"})


SEARCH_PAGE = rsc(
    '0:{"_value":"$L1"}',
    '3:I["./pages/search/search-page-content/results/index.tsx",'
    '["client-components.container.1","shared-node_modules_x.2","shared-pages_search_results.3"],"SearchResults"]',
    '7:I["./pages/search/search-page-params/search-page-params-provider.tsx",["shared-pages_search_params.4"],"P"]',
    '4:["$","$L7",null,{"params":{"dayOffset":"$undefined","searchId":"search-1","searchSessionId":"session-1",'
    '"searchTerm":"Affligem blond"},"children":["$","$L3",null,{}]}]',
)


def sellable(product_id: str, name: str, **fields: Any) -> dict[str, Any]:
    return {"type": "sellable", "id": product_id, "title": {"title": name, "prefix": "$undefined"}, **fields}


SEARCH_RESULTS = rsc(
    '1:I["./pages/search/search-page-content/results/search-store-container.tsx",[],"C"]',
    '0:["$","$L1",null,{"searchQuery":"Affligem blond","storeResults":{"SUPERMARKET":{"sections":['
    + ",".join(
        [
            '{"id":"Bier","items":['
            + json.dumps(
                sellable(
                    "s1001524",
                    "Affligem blond",
                    images={"primaryImage": {"imageId": "img-1"}},
                    price={"priceValue": 8.65, "priceRanges": [{"fromQuantity": 2, "price": 800}]},
                    suffixes=[{"type": "TEXT", "text": "6 x 300 ml"}, {"type": "ICON"}],
                )
            )
            + ',{"type":"banner"}]}',
            '{"id":"Bekijk ook","items":['
            + json.dumps(sellable("s1001525", "Affligem blond 0.0", price={"priceRanges": []}))
            + ","
            + json.dumps(sellable("s1001524", "Affligem blond"))
            + "]}",
        ]
    )
    + "]}}}]",
)


async def test_search_runs_the_search_pages_server_action(client: PicnicClient, api: MockApi) -> None:
    api.queue(
        SEARCH_PAGE,
        httpx.Response(
            status_code=200,
            json=samples.BOOTSTRAP | {"in_app_feature_config": {"client_component_cdn_base_url": "https://cdn.test/"}},
        ),
        httpx.Response(status_code=200, content=b'createServerReference("act_fetchSearchResults_abc123")'),
        SEARCH_RESULTS,
    )

    results = await client.catalog.search(query="Affligem blond")

    assert results == [
        SellingUnit(
            id="s1001524",
            name="Affligem blond",
            image_id="img-1",
            display_price=865,
            unit_quantity="6 x 300 ml",
            price_ranges=[PriceRange(price=800, from_quantity=2)],
        ),
        SellingUnit(id="s1001525", name="Affligem blond 0.0"),
    ]
    page, _, chunk, action = api.requests
    assert page.url.params["search_term"] == "Affligem blond"
    assert "x-picnic-agent" in page.headers
    assert str(chunk.url) == "https://cdn.test/shared-pages_search_results.3.script.bundle"
    assert "x-picnic-auth" not in chunk.headers
    assert action.url.path.endswith("/pages/action/act_fetchSearchResults_abc123")
    assert json.loads(json.loads(action.content)["params"]) == [
        {
            "requestedSorting": "RELEVANCE",
            "searchId": "search-1",
            "searchQuery": "Affligem blond",
            "searchSessionId": "session-1",
        }
    ]


async def test_search_caches_the_action_id_per_chunk(client: PicnicClient, api: MockApi) -> None:
    bootstrap = samples.BOOTSTRAP | {"in_app_feature_config": {"client_component_cdn_base_url": "https://cdn.test"}}
    api.queue(
        SEARCH_PAGE,
        httpx.Response(status_code=200, json=bootstrap),
        httpx.Response(status_code=200, content=b"act_fetchSearchResults_abc123"),
        SEARCH_RESULTS,
        SEARCH_PAGE,
        SEARCH_RESULTS,
    )

    await client.catalog.search(query="Affligem blond")
    await client.catalog.search(query="Affligem blond")

    assert len(api.requests) == 6


async def test_search_without_supermarket_results_returns_nothing(client: PicnicClient, api: MockApi) -> None:
    api.queue(
        SEARCH_PAGE,
        httpx.Response(
            status_code=200,
            json=samples.BOOTSTRAP | {"in_app_feature_config": {"client_component_cdn_base_url": "https://cdn.test"}},
        ),
        httpx.Response(status_code=200, content=b"act_fetchSearchResults_abc123"),
        rsc('0:["$","$L1",null,{"storeResults":{"SUPERMARKET":"$undefined","MEALS":{"sections":[]}}}]'),
    )

    assert await client.catalog.search(query="diepvries rood fruit gemengde bessen") == []


async def test_search_raises_when_the_page_has_no_action(client: PicnicClient, api: MockApi) -> None:
    api.queue(
        SEARCH_PAGE,
        httpx.Response(
            status_code=200,
            json=samples.BOOTSTRAP | {"in_app_feature_config": {"client_component_cdn_base_url": "https://cdn.test"}},
        ),
        httpx.Response(status_code=200, content=b"no action here"),
    )

    with pytest.raises(PicnicError, match="fetchSearchResults"):
        await client.catalog.search(query="Affligem blond")


@pytest.mark.parametrize(
    ("bootstrap_config", "chunk", "message"),
    [
        (None, None, "client_component_cdn_base_url"),
        ({"client_component_cdn_base_url": "https://cdn.test"}, httpx.Response(status_code=404), "404"),
    ],
)
async def test_search_raises_when_the_client_chunk_is_unreachable(
    client: PicnicClient, api: MockApi, bootstrap_config: dict[str, str] | None, chunk: Any, message: str
) -> None:
    api.queue(
        SEARCH_PAGE,
        httpx.Response(status_code=200, json=samples.BOOTSTRAP | {"in_app_feature_config": bootstrap_config}),
    )
    if chunk:
        api.queue(chunk)

    with pytest.raises(PicnicError, match=message):
        await client.catalog.search(query="Affligem blond")


async def test_get_product_details_fetches_and_parses_the_page(client: PicnicClient, api: MockApi) -> None:
    api.queue_json(full_product_page().raw())

    details = await client.catalog.get_product_details(product_id=PRODUCT_ID)

    assert details.name == "Blond"
    assert api.last.url.params["id"] == PRODUCT_ID


async def test_images(client: PicnicClient, api: MockApi) -> None:
    api.queue(httpx.Response(status_code=200, content=b"png"), httpx.Response(status_code=200, content=b"png"))

    assert await client.catalog.get_image(image_id="abc", size="small") == b"png"
    assert str(api.last.url) == "https://storefront-prod.nl.picnicinternational.com/static/images/abc/small.png"
    assert await client.catalog.get_image_as_data_uri(image_id="abc", size="small") == "data:image/png;base64,cG5n"


def test_extract_product_details_finds_a_wrapped_name() -> None:
    main_container = {
        "id": "product-details-page-root-main-container",
        "pml": {"component": {"children": [{"type": "TOUCHABLE", "child": text("Spinazie", textType="HEADER1")}]}},
    }

    details = extract_product_details(product_id=PRODUCT_ID, page=page(body={"children": [main_container]}))

    assert details.name == "Spinazie"
