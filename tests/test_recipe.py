import asyncio
import json
import math
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from picnic_api import PicnicClient, PicnicError
from picnic_api.domains.recipe.models import (
    NewUserDefinedRecipeIngredient,
    RecipeSummary,
    UserDefinedRecipeReferenceImage,
)
from tests import samples
from tests.conftest import MockApi

RECIPE_ID = "recipe-id"
UDR_ID = "3aa496368575423f9c5ed15e0c0c763e"
RECIPE_SCHEMA = "iglu:tech.picnic.snowplow.analytics/recipe/jsonschema/1-6-0"
SEGMENT_SCHEMA = "iglu:tech.picnic.snowplow.analytics/segment/jsonschema/1-0-0"


def details_page(
    portions: int, default_portions: int, product_id: str, name: str | None = None, creator_type: str = "PIM"
) -> dict[str, Any]:
    children: list[dict[str, Any]] = [
        {
            "data": {
                "creator_type": creator_type,
                "default_portions": default_portions,
                "is_saved": True,
                "sellable_name": "Recipe",
            }
        },
        {
            "data": {
                "recipe_id": RECIPE_ID,
                "recipe_name": "Recipe",
                "portions": portions,
                "selling_units": [
                    {
                        "ingredient_id": "ingredient",
                        "selling_unit_id": product_id,
                        "quantity": 1 if portions == 4 else 2,
                        "checked": True,
                    }
                ],
            }
        },
        {
            "id": "selling-group-details-image",
            "type": "PML",
            "pml": {"component": {"type": "IMAGE", "source": {"id": f"recipes/image-{portions}"}}},
        },
    ]
    if name:
        children.append(
            {
                "type": "PML",
                "id": "core-wide-selling-unit-tile-ingredient",
                "analytics": {
                    "contexts": [
                        {
                            "schema": RECIPE_SCHEMA,
                            "data": {"selling_units": [{"ingredient_id": "ingredient", "selling_unit_id": product_id}]},
                        }
                    ]
                },
                "pml": {"component": {"type": "RICH_TEXT", "textType": "SUBTITLE1", "markdown": name}},
            }
        )
    return {"script": {}, "layout": {"body": {"children": children}}}


def product_page(name: str) -> dict[str, Any]:
    return {"layout": {"body": {"type": "RICH_TEXT", "textType": "HEADER1", "markdown": name}}}


@pytest.mark.parametrize(argnames="creator_type", argvalues=["PIM", "USER"])
async def test_refetches_at_the_default_portions(client: PicnicClient, api: MockApi, creator_type: str) -> None:
    api.queue_json(
        details_page(
            portions=2, default_portions=4, product_id="small-pack", name="Small pack", creator_type=creator_type
        ),
        details_page(
            portions=4, default_portions=4, product_id="large-pack", name="Large pack", creator_type=creator_type
        ),
    )

    if creator_type == "USER":
        details = await client.recipe.get_user_defined_recipe(recipe_id=RECIPE_ID)
    else:
        details = await client.recipe.get_recipe(recipe_id=RECIPE_ID)

    assert len(api.requests) == 2
    assert api.last.url.params["portions"] == "4"
    assert (details.portions, details.default_portions, details.displayed_portions) == (4, 4, 4)
    assert details.image_id == "recipes/image-4"
    assert details.creator_type == creator_type
    ingredient = details.ingredients[0]
    assert (ingredient.selling_unit_id, ingredient.name, ingredient.quantity) == ("large-pack", "Large pack", 1)


@pytest.mark.parametrize(argnames="method", argvalues=["get_recipe", "get_user_defined_recipe"])
async def test_explicit_portions_need_a_single_request(client: PicnicClient, api: MockApi, method: str) -> None:
    api.queue_json(details_page(portions=2, default_portions=4, product_id="small-pack"))

    details = await getattr(client.recipe, method)(recipe_id=RECIPE_ID, portions=2)

    assert len(api.requests) == 1
    assert api.last.url.params["portions"] == "2"
    assert (details.portions, details.default_portions) == (2, 4)
    assert details.ingredients[0].name is None


async def test_does_not_refetch_when_the_default_matches(client: PicnicClient, api: MockApi) -> None:
    api.queue_json(details_page(portions=4, default_portions=4, product_id="product"))

    await client.recipe.get_recipe(recipe_id=RECIPE_ID)

    assert len(api.requests) == 1
    assert "portions" not in api.last.url.params


@pytest.mark.parametrize(argnames="portions", argvalues=[0, -1, 1.5, math.nan, math.inf, True])
async def test_rejects_invalid_portions_before_a_request(client: PicnicClient, api: MockApi, portions: Any) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        await client.recipe.get_recipe(recipe_id=RECIPE_ID, portions=portions)

    assert api.requests == []


async def test_bounds_refetching_when_the_server_ignores_portions(client: PicnicClient, api: MockApi) -> None:
    api.fallback = lambda request: httpx.Response(
        status_code=200, json=details_page(portions=2, default_portions=4, product_id="product")
    )

    with pytest.raises(PicnicError, match="rendered 2 portions instead of 4"):
        await client.recipe.get_recipe(recipe_id=RECIPE_ID, portions=4)

    assert len(api.requests) == 2


async def test_propagates_page_rendering_errors(client: PicnicClient, api: MockApi) -> None:
    message = "Error rendering page_id='selling-group-details-page'"
    api.queue(httpx.Response(status_code=500, json={"error": {"message": message}}))

    with pytest.raises(PicnicError, match=message):
        await client.recipe.get_user_defined_recipe(recipe_id=RECIPE_ID, portions=2)

    assert len(api.requests) == 1


async def test_name_lookups_run_concurrently_once_per_product(client: PicnicClient, api: MockApi) -> None:
    data = details_page(portions=4, default_portions=4, product_id="first")
    units = data["layout"]["body"]["children"][1]["data"]["selling_units"]
    units.extend(
        [
            units[0] | {"ingredient_id": "second", "selling_unit_id": "second"},
            units[0] | {"ingredient_id": "duplicate"},
        ]
    )
    both_in_flight = asyncio.Barrier(parties=2)

    async def product(request: httpx.Request) -> httpx.Response:
        async with asyncio.timeout(delay=5):
            await both_in_flight.wait()
        return httpx.Response(status_code=200, json=product_page(name=f"Product {request.url.params['id']}"))

    api.queue_json(data)
    api.fallback = product

    details = await client.recipe.get_user_defined_recipe(recipe_id=RECIPE_ID, resolve_ingredient_names=True)

    assert len(api.requests) == 3
    assert [ingredient.name for ingredient in details.ingredients] == [
        "Product first",
        "Product second",
        "Product first",
    ]


async def test_name_lookup_errors_propagate(client: PicnicClient, api: MockApi) -> None:
    api.queue_json(details_page(portions=4, default_portions=4, product_id="product"))
    api.queue(httpx.Response(status_code=404, json={"error": {"message": "Product unavailable"}}))

    with pytest.raises(PicnicError, match="Product unavailable"):
        await client.recipe.get_recipe(recipe_id=RECIPE_ID, resolve_ingredient_names=True)


async def test_name_lookup_without_a_name_stays_none(client: PicnicClient, api: MockApi) -> None:
    api.queue_json(details_page(portions=4, default_portions=4, product_id="product"), {"layout": {"body": {}}})

    details = await client.recipe.get_recipe(recipe_id=RECIPE_ID, resolve_ingredient_names=True)

    assert details.ingredients[0].name is None


async def test_name_lookups_are_skipped_when_names_are_known(client: PicnicClient, api: MockApi) -> None:
    api.queue_json(details_page(portions=4, default_portions=4, product_id="product", name="Known"))

    details = await client.recipe.get_recipe(recipe_id=RECIPE_ID, resolve_ingredient_names=True)

    assert len(api.requests) == 1
    assert details.ingredients[0].name == "Known"


@pytest.mark.parametrize(
    argnames=("method", "segment"),
    argvalues=[("get_saved_recipes", "SAVED_RECIPES"), ("get_user_defined_recipes", "USER_DEFINED_RECIPES")],
)
async def test_recipe_lists_select_their_cookbook_segment(
    client: PicnicClient, api: MockApi, method: str, segment: str
) -> None:
    def tile(segment_type: str, recipe_id: str) -> dict[str, Any]:
        return {
            "analytics": {
                "contexts": [
                    {"schema": SEGMENT_SCHEMA, "data": {"segment_type": segment_type}},
                    {"schema": RECIPE_SCHEMA, "data": {"recipe_id": recipe_id, "recipe_name": recipe_id}},
                ]
            }
        }

    api.queue_json({"layout": {"body": {"children": [tile(segment, "wanted"), tile("NEW_RECIPES", "other")]}}})

    assert await getattr(client.recipe, method)() == [RecipeSummary(id="wanted", name="wanted", image_type=None)]
    assert api.last.url.path.endswith("/pages/cookbook-page-content")


async def test_save_recipe_sends_the_current_timestamp(client: PicnicClient, api: MockApi) -> None:
    await client.recipe.save_recipe(recipe_id="r1")

    payload = api.last_json()["payload"]
    saved_at = datetime.fromisoformat(payload["saved_at"])
    assert payload["recipe_id"] == "r1"
    assert payload["saved_at"].endswith("Z")
    assert abs((datetime.now(tz=UTC) - saved_at).total_seconds()) < 60


async def test_create_user_defined_recipe(client: PicnicClient, api: MockApi) -> None:
    api.queue_json({"sellingGroupId": UDR_ID})

    result = await client.recipe.create_user_defined_recipe(
        name="Testrecept",
        ingredients=[
            NewUserDefinedRecipeIngredient(selling_unit_id="s1143210", quantity=2, source="usuals-suggestion"),
            NewUserDefinedRecipeIngredient(selling_unit_id="s1189145"),
        ],
    )

    assert api.last.url.path.endswith("/pages/task/create-user-defined-recipe")
    assert api.last.method == "POST"
    assert api.last_json() == {
        "payload": {
            "name": "Testrecept",
            "portions": 4,
            "selling_unit_quantities_by_id": {"s1143210": 2, "s1189145": 1},
            "selling_unit_sources": {"s1143210": "usuals-suggestion", "s1189145": "search"},
            "selling_units": ["s1143210", "s1189145"],
        }
    }
    assert result.selling_group_id == UDR_ID


async def test_update_ingredient_sends_the_swap_type_only_when_given(client: PicnicClient, api: MockApi) -> None:
    api.queue_json({"shouldUpdateCart": True, "cart": samples.SELLING_GROUP_CART}, {})
    ingredient_id = "88c457541b974e8ab682e0a449a2d94c"

    result = await client.recipe.update_user_defined_recipe_ingredient(
        recipe_id=UDR_ID,
        ingredient_id=ingredient_id,
        selling_unit_quantities={"s1143210": 0, "s1189145": 1},
        portions=2,
        swap_type="SEARCH_SELECTION",
    )
    assert result.should_update_cart is True
    assert result.cart is not None
    assert result.cart.selling_units["s1"].contexts
    assert api.last_json()["payload"]["swapType"] == "SEARCH_SELECTION"
    assert api.last_json()["payload"]["selling_unit_quantity_by_id"] == {"s1143210": 0, "s1189145": 1}

    await client.recipe.update_user_defined_recipe_ingredient(
        recipe_id=UDR_ID, ingredient_id=ingredient_id, selling_unit_quantities={"s1143210": 2}
    )
    assert api.last.url.path.endswith("/pages/task/save-selling-group-edit-task")
    assert api.last_json() == {
        "payload": {
            "requested_sellable_portions": "4",
            "selling_group_component_id": ingredient_id,
            "selling_group_id": UDR_ID,
            "selling_unit_quantity_by_id": {"s1143210": 2},
        }
    }


async def test_suggested_images_come_from_the_selection_page(client: PicnicClient, api: MockApi) -> None:
    reference = {
        "id": "a" * 64,
        "namespace": "recipes",
        "primary_image": True,
        "rank_value": 1,
        "sellable_id": "69738f92ca0c63178b4a67a9",
        "type": "GALLERY",
    }
    api.queue_json(
        {
            "id": "sellable-image-selection-page-root",
            "body": {
                "children": [
                    {
                        "type": "STATE_BOUNDARY",
                        "id": "ImageSelectionState",
                        "state": {"referenceImagesById": {reference["id"]: reference}},
                    }
                ]
            },
        }
    )

    images = await client.recipe.get_user_defined_recipe_suggested_images(recipe_id=UDR_ID)

    assert api.last.url.path.endswith("/pages/sellable-image-selection-page-root")
    assert dict(api.last.url.params) == {"origin": "RECIPE_DETAILS", "sellable_id": UDR_ID}
    assert [image.id for image in images] == [reference["id"]]
    assert images[0].reference_image.raw() == reference


async def test_select_image_sends_the_reference_image(client: PicnicClient, api: MockApi) -> None:
    reference = UserDefinedRecipeReferenceImage(
        id="img", namespace="recipes", primary_image=True, rank_value=1, sellable_id="s", type="GALLERY"
    )

    await client.recipe.select_user_defined_recipe_image(recipe_id=UDR_ID, image_id="img", reference_image=reference)

    assert api.last_json()["payload"] == {
        "sellable_id": UDR_ID,
        "selected_image_id": "img",
        "reference_image": reference.model_dump(),
    }


@pytest.mark.parametrize(argnames="response_key", argvalues=["image_id", "imageId"])
async def test_upload_image_posts_raw_bytes(client: PicnicClient, api: MockApi, response_key: str) -> None:
    api.queue_json({response_key: "img-1", "namespace": "sellable-customer-uploaded"})

    result = await client.recipe.upload_user_defined_recipe_image(
        recipe_id=UDR_ID, data=b"\x01\x02\x03", content_type="image/JPG"
    )

    assert api.last.url.path.endswith(f"/user-defined-sellable/{UDR_ID}")
    assert api.last.method == "POST"
    assert api.last.content == b"\x01\x02\x03"
    assert api.last.headers["Content-Type"] == "image/jpeg"
    assert api.last.headers["x-picnic-auth"] == "initial-auth-key"
    assert "x-picnic-agent" in api.last.headers
    assert result.image_id == "img-1"
    assert json.loads(result.model_dump_json())["image_id"] == "img-1"
