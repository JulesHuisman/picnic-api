import json
import re
from typing import Any

from picnic_api.domains.recipe.models import (
    RecipeDetails,
    RecipeIngredient,
    RecipeSegment,
    RecipeSummary,
    UserDefinedRecipeReferenceImage,
    UserDefinedRecipeSuggestedImage,
)
from picnic_api.errors import PicnicError
from picnic_api.json_tree import iter_objects
from picnic_api.models.fusion import FusionPage

RECIPE_SCHEMA = "iglu:tech.picnic.snowplow.analytics/recipe/jsonschema/"
SEGMENT_SCHEMA = "iglu:tech.picnic.snowplow.analytics/segment/jsonschema/"
COLOR_MARKUP = re.compile(r"#\([^)]*\)")
INGREDIENT_ID_IN_URL = re.compile(r"ingredient_id=([a-f0-9-]+)&")


def extract_recipes(page: FusionPage, segment_type: RecipeSegment) -> list[RecipeSummary]:
    """Extracts the recipes of a cookbook segment in tile order, deduplicated by recipe id.

    Catalog tiles often omit `recipe_name` from their analytics; the tile's SUBTITLE1 text holds it then.
    """
    recipes: dict[str, RecipeSummary] = {}
    for obj in iter_objects(node=page.raw()):
        analytics = obj.get("analytics")
        contexts = analytics.get("contexts") if isinstance(analytics, dict) else None
        contexts = contexts if contexts is not None else obj.get("contexts")
        if not isinstance(contexts, list):
            continue
        segment = _context_data(contexts=contexts, schema=SEGMENT_SCHEMA)
        recipe = _context_data(contexts=contexts, schema=RECIPE_SCHEMA)
        if segment.get("segment_type") != segment_type or not isinstance(recipe.get("recipe_id"), str):
            continue

        previous = recipes.get(recipe["recipe_id"])
        image_type = previous.image_type if previous else None
        if image_type is None:
            image_type = _coalesce(recipe.get("recipe_image_type"), recipe.get("image_type"))
        recipes[recipe["recipe_id"]] = RecipeSummary(
            id=recipe["recipe_id"],
            name=(previous.name if previous else "")
            or recipe.get("recipe_name")
            or _text_by_type(node=obj.get("pml"), text_type="SUBTITLE1")
            or "",
            image_type=image_type,
        )
    return list(recipes.values())


def extract_ingredient_product_name(page: FusionPage) -> str | None:
    """Returns the product name of a product details page, used for ingredients without a visible tile."""
    return _text_by_type(node=page.raw(), text_type="HEADER1")


def extract_recipe_details(recipe_id: str, page: FusionPage) -> RecipeDetails:
    """Extracts structured details of a catalog or user-defined recipe from its `selling-group-details-page`.

    The page embeds the recipe as an analytics `recipe` context (name, displayed portions, image type and all
    selling units), a header object with `creator_type`, `default_portions` and `is_saved`, an
    `is_recipe_owner` flag and, when present, the note as the `initialContent` of a `TEXT_EDITOR` component.
    Changing the portion count may select different products, not merely scale quantities.
    """
    raw = page.raw()
    recipe_context: dict[str, Any] | None = None
    header: dict[str, Any] = {}
    owner: dict[str, Any] = {}
    note: str | None = None
    image_id: str | None = None

    for obj in iter_objects(node=raw):
        if obj.get("id") == "selling-group-details-image" and image_id is None:
            image_id = _main_image_id(node=obj)
        if (
            recipe_context is None
            and obj.get("recipe_id") == recipe_id
            and isinstance(obj.get("selling_units"), list)
            and isinstance(obj.get("recipe_name"), str)
        ):
            recipe_context = obj
        if not header and isinstance(obj.get("creator_type"), str) and isinstance(obj.get("sellable_name"), str):
            header = obj
        if not owner and isinstance(obj.get("is_recipe_owner"), bool) and isinstance(obj.get("name"), str):
            owner = obj
        if note is None and obj.get("type") == "TEXT_EDITOR" and isinstance(obj.get("initialContent"), str):
            note = obj["initialContent"]

    if recipe_context is None:
        raise PicnicError(f"Could not extract recipe {recipe_id}: recipe context missing from details page")

    names = _extract_ingredient_names(raw=raw)
    portions = _coalesce(recipe_context.get("portions"), header.get("default_portions"), 0)
    return RecipeDetails(
        id=recipe_id,
        name=_coalesce(recipe_context.get("recipe_name"), header.get("sellable_name"), owner.get("name"), ""),
        portions=portions,
        default_portions=_coalesce(header.get("default_portions"), recipe_context.get("portions"), 0),
        displayed_portions=portions,
        creator_type=_coalesce(header.get("creator_type"), "UNKNOWN"),
        is_recipe_owner=_coalesce(owner.get("is_recipe_owner"), False),
        is_saved=_coalesce(header.get("is_saved"), False),
        image_type=recipe_context.get("image_type"),
        image_id=image_id,
        ingredients=[
            RecipeIngredient(
                ingredient_id=unit.get("ingredient_id"),
                name=names.get(unit.get("ingredient_id")),
                selling_unit_id=_coalesce(unit.get("selling_unit_id"), ""),
                quantity=_coalesce(unit.get("quantity"), 1),
                status=_coalesce(unit.get("status"), "ACTIVE"),
                swap_type=unit.get("swap_type"),
                checked=_coalesce(unit.get("checked"), True),
            )
            for unit in recipe_context["selling_units"]
        ],
        note=note,
    )


def extract_ingredient_quantities(page: Any) -> dict[str, dict[str, int]]:
    """Returns ingredient id to (selling unit id to required amount) from a `sellableContentState` boundary.

    The amounts are scaled to the portions the page was requested with.
    """
    quantities: dict[str, dict[str, int]] = {}
    for obj in iter_objects(node=page):
        if obj.get("type") != "STATE_BOUNDARY" or obj.get("id") != "sellableContentState":
            continue
        for ingredient in (obj.get("state") or {}).get("ingredientsState") or []:
            if (
                not isinstance(ingredient, dict)
                or not ingredient.get("ingredientId")
                or not ingredient.get("sellingUnits")
            ):
                continue
            quantities[ingredient["ingredientId"]] = {
                unit["sellingUnitId"]: _coalesce(unit.get("requiredAmount"), 0)
                for unit in ingredient["sellingUnits"].values()
            }
    return quantities


def extract_suggested_images(page: Any) -> list[UserDefinedRecipeSuggestedImage]:
    """Returns the suggested images from the `ImageSelectionState` boundary of the image selection page."""
    images = []
    for obj in iter_objects(node=page):
        if obj.get("type") != "STATE_BOUNDARY" or obj.get("id") != "ImageSelectionState":
            continue
        for reference in ((obj.get("state") or {}).get("referenceImagesById") or {}).values():
            if isinstance(reference, dict) and reference.get("id"):
                images.append(
                    UserDefinedRecipeSuggestedImage(
                        id=reference["id"],
                        reference_image=UserDefinedRecipeReferenceImage.model_validate(obj=reference),
                    )
                )
    return images


def _coalesce(*values: Any) -> Any:
    return next((value for value in values if value is not None), None)


def _context_data(contexts: list[Any], schema: str) -> dict[str, Any]:
    for context in contexts:
        if isinstance(context, dict) and str(context.get("schema") or "").startswith(schema):
            data = context.get("data")
            return data if isinstance(data, dict) else {}
    return {}


def _plain_text(markdown: str) -> str:
    return COLOR_MARKUP.sub("", markdown).replace("**", "").replace("\u00a0", " ").strip()


def _text_by_type(node: Any, text_type: str) -> str | None:
    for obj in iter_objects(node=node):
        is_text = obj.get("type") == "RICH_TEXT" and obj.get("textType") == text_type
        if is_text and isinstance(obj.get("markdown"), str) and (text := _plain_text(markdown=obj["markdown"])):
            return text
    return None


def _main_image_id(node: dict[str, Any]) -> str | None:
    for image in iter_objects(node=node):
        source = image.get("source")
        if image.get("type") == "IMAGE" and isinstance(source, dict) and isinstance(source.get("id"), str):
            return source["id"]
    return None


def _extract_ingredient_names(raw: dict[str, Any]) -> dict[str, str]:
    """Returns ingredient names keyed by component id, read from the ingredient tiles.

    Discontinued tiles omit analytics, but their edit link still carries the component id, which is read from
    the PML as text without executing it.
    """
    names: dict[str, str] = {}
    for obj in iter_objects(node=raw):
        tile_id = obj.get("id")
        if obj.get("type") != "PML" or not isinstance(tile_id, str) or "selling-unit-tile" not in tile_id:
            continue
        analytics = obj.get("analytics")
        contexts = (analytics.get("contexts") if isinstance(analytics, dict) else None) or []
        units = _context_data(contexts=contexts, schema=RECIPE_SCHEMA).get("selling_units")
        if isinstance(units, list) and len(units) == 1:
            ingredient_id = units[0].get("ingredient_id")
        else:
            match = INGREDIENT_ID_IN_URL.search(json.dumps(obj=_coalesce(obj.get("pml"), {})))
            ingredient_id = match.group(1) if match else None
        name = _text_by_type(node=obj.get("pml"), text_type="SUBTITLE1")
        if isinstance(ingredient_id, str) and name:
            names[ingredient_id] = name
    return names
