from typing import Any

import pytest

from picnic_api import PicnicError
from picnic_api.domains.recipe.helpers import (
    extract_ingredient_product_name,
    extract_ingredient_quantities,
    extract_recipe_details,
    extract_recipes,
    extract_suggested_images,
)
from picnic_api.domains.recipe.models import (
    RecipeDetails,
    RecipeIngredient,
    RecipeSummary,
    UserDefinedRecipeReferenceImage,
    UserDefinedRecipeSuggestedImage,
)
from picnic_api.models.fusion import FusionPage

RECIPE_SCHEMA = "iglu:tech.picnic.snowplow.analytics/recipe/jsonschema/1-6-0"
SEGMENT_SCHEMA = "iglu:tech.picnic.snowplow.analytics/segment/jsonschema/1-0-0"


def page(body: Any) -> FusionPage:
    return FusionPage.model_validate(
        obj={"script": {}, "layout": {"id": "p", "presentation": {"type": "FULL_SCREEN"}, "header": None, "body": body}}
    )


def tile(recipe: dict[str, Any], segment_type: str, **extra: Any) -> dict[str, Any]:
    return {
        "analytics": {
            "contexts": [
                {"data": recipe, "schema": RECIPE_SCHEMA},
                {"data": {"segment_type": segment_type}, "schema": SEGMENT_SCHEMA},
            ]
        },
        **extra,
    }


def test_extract_recipes_picks_one_segment_deduplicated_in_order() -> None:
    def own(recipe_id: str, name: str) -> dict[str, Any]:
        return tile(
            recipe={"recipe_id": recipe_id, "recipe_image_type": "GALLERY", "recipe_name": name},
            segment_type="USER_DEFINED_RECIPES",
        )

    saved = tile(
        recipe={"recipe_id": "6a1ee3b78d45fb1080af7898", "recipe_name": "Catalog"}, segment_type="SAVED_RECIPES"
    )
    body = {"children": [own("a" * 32, "Kaasplank"), saved, own("a" * 32, "Kaasplank"), own("b" * 32, "Hamburgers")]}

    assert extract_recipes(page=page(body=body), segment_type="USER_DEFINED_RECIPES") == [
        RecipeSummary(id="a" * 32, name="Kaasplank", image_type="GALLERY"),
        RecipeSummary(id="b" * 32, name="Hamburgers", image_type="GALLERY"),
    ]


def test_extract_recipes_reads_names_from_tile_titles() -> None:
    saved = tile(
        recipe={"recipe_id": "saved"},
        segment_type="SAVED_RECIPES",
        pml={"component": {"type": "RICH_TEXT", "textType": "SUBTITLE1", "markdown": "#(#333333)**Pasta**#(#333333)"}},
    )
    plain_contexts = {"contexts": saved["analytics"]["contexts"]}

    assert extract_recipes(
        page=page(body={"children": [saved, saved, plain_contexts]}), segment_type="SAVED_RECIPES"
    ) == [RecipeSummary(id="saved", name="Pasta", image_type=None)]
    assert extract_recipes(page=page(body=saved), segment_type="USER_DEFINED_RECIPES") == []


def test_extract_recipe_details_combines_context_header_owner_and_note() -> None:
    recipe_id = "3aa496368575423f9c5ed15e0c0c763e"
    body = {
        "children": [
            {
                "data": {
                    "creator_type": "USER",
                    "default_portions": 2,
                    "is_saved": False,
                    "sellable_name": "Avocadopasta",
                }
            },
            {"data": {"description": None, "is_recipe_owner": True, "name": "Avocadopasta"}},
            {
                "data": {
                    "image_type": "SUGGESTED",
                    "portions": 4,
                    "recipe_id": recipe_id,
                    "recipe_name": "Avocadopasta",
                    "selling_units": [
                        {
                            "checked": True,
                            "ingredient_id": "88c457541b974e8ab682e0a449a2d94c",
                            "quantity": 1,
                            "selling_unit_id": "s1143210",
                            "status": "ACTIVE",
                            "swap_type": None,
                        },
                        {
                            "checked": False,
                            "ingredient_id": "54edeceb41c04ca78cd06bc6b189aa8b",
                            "quantity": 2,
                            "selling_unit_id": "s1189145",
                            "status": "UNAVAILABLE",
                            "swap_type": "SIMILAR",
                        },
                    ],
                }
            },
            {"editable": False, "initialContent": "<p>400g pasta</p>", "type": "TEXT_EDITOR"},
        ]
    }

    assert extract_recipe_details(recipe_id=recipe_id, page=page(body=body)) == RecipeDetails(
        id=recipe_id,
        name="Avocadopasta",
        portions=4,
        default_portions=2,
        displayed_portions=4,
        creator_type="USER",
        is_recipe_owner=True,
        is_saved=False,
        image_type="SUGGESTED",
        image_id=None,
        ingredients=[
            RecipeIngredient(
                ingredient_id="88c457541b974e8ab682e0a449a2d94c",
                name=None,
                selling_unit_id="s1143210",
                quantity=1,
                status="ACTIVE",
                swap_type=None,
                checked=True,
            ),
            RecipeIngredient(
                ingredient_id="54edeceb41c04ca78cd06bc6b189aa8b",
                name=None,
                selling_unit_id="s1189145",
                quantity=2,
                status="UNAVAILABLE",
                swap_type="SIMILAR",
                checked=False,
            ),
        ],
        note="<p>400g pasta</p>",
    )


def test_extract_recipe_details_defaults_without_header_or_owner() -> None:
    body = {"data": {"recipe_id": "r", "recipe_name": "R", "selling_units": [{"ingredient_id": "i"}]}}

    details = extract_recipe_details(recipe_id="r", page=page(body=body))

    assert (details.portions, details.default_portions, details.creator_type) == (0, 0, "UNKNOWN")
    assert (details.is_recipe_owner, details.is_saved, details.note) == (False, False, None)
    assert details.ingredients[0] == RecipeIngredient(
        ingredient_id="i", name=None, selling_unit_id="", quantity=1, status="ACTIVE", swap_type=None, checked=True
    )


def test_extract_recipe_details_requires_the_recipe_context() -> None:
    with pytest.raises(PicnicError, match="recipe context missing"):
        extract_recipe_details(recipe_id="missing", page=page(body={"children": []}))


@pytest.mark.parametrize(
    argnames="image_id", argvalues=["recipes/catalog-photo", "sellable-customer-uploaded/own-photo"]
)
def test_extract_recipe_details_picks_the_main_image_only(image_id: str) -> None:
    body = {
        "children": [
            {"type": "IMAGE", "source": {"id": "articles/ingredient-photo"}},
            {"id": "selling-group-details-image", "pml": {"component": {"type": "IMAGE", "source": {"id": image_id}}}},
            {"data": {"recipe_id": "recipe", "recipe_name": "Recipe", "portions": 2, "selling_units": []}},
        ]
    }

    assert extract_recipe_details(recipe_id="recipe", page=page(body=body)).image_id == image_id


def test_extract_recipe_details_has_no_image_when_hidden() -> None:
    body = {
        "children": [
            {"id": "selling-group-details-image-hidden", "type": "BLOCK", "children": []},
            {"id": "selling-group-details-image", "children": []},
            {"type": "IMAGE", "source": {"id": "articles/product-image"}},
            {"data": {"recipe_id": "recipe", "recipe_name": "Recipe", "portions": 4, "selling_units": []}},
        ]
    }

    assert extract_recipe_details(recipe_id="recipe", page=page(body=body)).image_id is None


def test_extract_recipe_details_names_discontinued_ingredients_without_executing_pml() -> None:
    ingredient_id = "a" * 32
    body = {
        "children": [
            {
                "data": {
                    "recipe_id": "recipe",
                    "recipe_name": "Recipe",
                    "portions": 2,
                    "selling_units": [
                        {"ingredient_id": ingredient_id, "selling_unit_id": "", "quantity": 0, "checked": False}
                    ],
                }
            },
            {
                "type": "PML",
                "id": "core-wide-selling-unit-tile-unsellable-0",
                "pml": {
                    "component": {"type": "RICH_TEXT", "textType": "SUBTITLE1", "markdown": "Old\u00a0product"},
                    "expression": f'throw new Error("Do not execute"); // ingredient_id={ingredient_id}&is_udr=true',
                },
            },
            {"type": "PML", "id": "core-wide-selling-unit-tile-nameless", "pml": None},
        ]
    }

    ingredient = extract_recipe_details(recipe_id="recipe", page=page(body=body)).ingredients[0]

    assert (ingredient.name, ingredient.selling_unit_id, ingredient.quantity, ingredient.checked) == (
        "Old product",
        "",
        0,
        False,
    )


def test_extract_ingredient_quantities_reads_required_amounts() -> None:
    wrapper = {
        "type": "STATE_BOUNDARY",
        "id": "sellableContentState",
        "state": {
            "ingredientsState": [
                {"ingredientId": "ing-1", "sellingUnits": {"s1": {"sellingUnitId": "s1", "requiredAmount": 1}}},
                {
                    "ingredientId": "ing-2",
                    "sellingUnits": {
                        "s2": {"sellingUnitId": "s2", "requiredAmount": 2},
                        "s3": {"sellingUnitId": "s3"},
                    },
                },
                {"ingredientId": "ing-3"},
            ]
        },
    }

    assert extract_ingredient_quantities(page={"child": wrapper, "other": {"type": "STATE_BOUNDARY"}}) == {
        "ing-1": {"s1": 1},
        "ing-2": {"s2": 2, "s3": 0},
    }


def test_extract_suggested_images_reads_reference_images() -> None:
    first = {
        "id": "1" * 64,
        "namespace": "recipes",
        "primary_image": True,
        "rank_value": 1,
        "sellable_id": "69738f92ca0c63178b4a67a9",
        "type": "GALLERY",
    }
    second = first | {"id": "2" * 64, "rank_value": 10}
    layout = {
        "body": {
            "children": [
                {"type": "STATE_BOUNDARY", "id": "GlobalState", "state": {}},
                {
                    "type": "STATE_BOUNDARY",
                    "id": "ImageSelectionState",
                    "state": {"referenceImagesById": {first["id"]: first, second["id"]: second, "x": {}}},
                },
            ]
        }
    }

    assert extract_suggested_images(page=layout) == [
        UserDefinedRecipeSuggestedImage(id=first["id"], reference_image=UserDefinedRecipeReferenceImage(**first)),
        UserDefinedRecipeSuggestedImage(id=second["id"], reference_image=UserDefinedRecipeReferenceImage(**second)),
    ]
    assert extract_suggested_images(page={"body": {}}) == []


def test_extract_ingredient_product_name_reads_the_header() -> None:
    product_page = page(
        body={
            "children": [
                {"type": "RICH_TEXT", "textType": "HEADER1", "markdown": " "},
                {"type": "RICH_TEXT", "textType": "HEADER1", "markdown": "Basilicum"},
            ]
        }
    )

    assert extract_ingredient_product_name(page=product_page) == "Basilicum"
    assert extract_ingredient_product_name(page=page(body={})) is None
