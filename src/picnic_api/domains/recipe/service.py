import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from picnic_api.domains.catalog.service import CatalogService
from picnic_api.domains.recipe.helpers import (
    extract_ingredient_product_name,
    extract_recipe_details,
    extract_recipes,
    extract_suggested_images,
)
from picnic_api.domains.recipe.models import (
    AddUserDefinedRecipeIngredientResult,
    AssignSellableComponentToDayResult,
    AssignSellingGroupToBasketResult,
    CreateUserDefinedRecipeResult,
    NewUserDefinedRecipeIngredient,
    RecipeDetails,
    RecipeSummary,
    RemoveSellingGroupFromBasketResult,
    RemoveUserDefinedRecipeIngredientResult,
    SellingGroupSwapType,
    UpdateUserDefinedRecipeIngredientResult,
    UserDefinedRecipeImageUploadResult,
    UserDefinedRecipeReferenceImage,
    UserDefinedRecipeSuggestedImage,
)
from picnic_api.errors import PicnicError
from picnic_api.http_client import HttpClient
from picnic_api.models.fusion import FusionPage, FusionPageLayout

JPG = re.compile(r"jpg", re.IGNORECASE)


class RecipeService:
    """Recipe browsing and saving, plus creating and editing the user's own (user defined) recipes."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def get_recipes_page(self) -> FusionPage:
        """Returns the meal planner root page. Its recipes load lazily; use `get_cookbook_page` to list recipes."""
        return self._get_page(path="/pages/meals-page-root")

    def get_cookbook_page(self) -> FusionPage:
        """Returns the cookbook page, listing the user's recipes grouped by segment.

        Each recipe tile carries a `segment_type` analytics context, e.g. `SAVED_RECIPES`, `USER_DEFINED_RECIPES`,
        `NEW_RECIPES` or `THIS_WEEK_RECIPES`.
        """
        return self._get_page(path="/pages/cookbook-page-content")

    def get_recipe_details_page(self, recipe_id: str, portions: int | None = None) -> FusionPage:
        """Returns the detail page of a recipe: ingredients, cooking steps, servings, cooking time and pricing.

        `recipe_id` is a selling group id (24 hex chars for catalog recipes, 32 for the user's own recipes).
        `portions` renders that many portions; omit it to use the app's selection.
        """
        if portions is not None and (isinstance(portions, bool) or not isinstance(portions, int) or portions <= 0):
            raise ValueError("Recipe portions must be a positive integer")
        query = "" if portions is None else f"&portions={portions}"
        return self._get_page(
            path=f"/pages/selling-group-details-page?selling_group_id={quote(recipe_id, safe='')}{query}"
        )

    def get_saved_recipes(self) -> list[RecipeSummary]:
        """Lists the saved recipes from the cookbook's `SAVED_RECIPES` segment. Use `get_recipe` for details."""
        return extract_recipes(page=self.get_cookbook_page(), segment_type="SAVED_RECIPES")

    def get_recipe(
        self, recipe_id: str, portions: int | None = None, resolve_ingredient_names: bool = False
    ) -> RecipeDetails:
        """Returns structured details of a catalog or user-defined recipe at `portions`, or its stored default.

        When the app renders a different count than requested, the page is fetched again so names, products and
        quantities all come from the same response. Products may change with the portion count.

        Ingredient names come from recipe tiles. Set `resolve_ingredient_names` to look up missing names on the
        product pages concurrently; a failing lookup fails the call. Quantities are selling-unit counts.
        This parses dynamic Fusion pages and may need updates when Picnic changes them. Some recipes reject
        particular portion counts with a page rendering error.
        """
        details = self._get_recipe_details(recipe_id=recipe_id, portions=portions)
        requested_portions = portions if portions is not None else details.default_portions
        if details.portions != requested_portions:
            details = self._get_recipe_details(recipe_id=recipe_id, portions=requested_portions)
        if details.portions != requested_portions:
            raise PicnicError(
                f"Recipe {recipe_id} rendered {details.portions} portions instead of {requested_portions}"
            )
        return self._with_product_names(details=details) if resolve_ingredient_names else details

    def save_recipe(self, recipe_id: str) -> None:
        """Adds a recipe to the user's saved recipes."""
        saved_at = datetime.now(tz=UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        self._run_task(task="recipe-saving", payload={"recipe_id": recipe_id, "saved_at": saved_at})

    def unsave_recipe(self, recipe_id: str) -> None:
        """Removes a recipe from the user's saved recipes."""
        self._run_task(task="recipe-saving", payload={"recipe_id": recipe_id, "saved_at": None})

    def assign_selling_group_to_basket(
        self, selling_group_id: str, day_offset: int | None = None, portions: int | None = None
    ) -> AssignSellingGroupToBasketResult:
        """Adds a recipe to the basket in the meal planner, for the delivery day `day_offset` from the slot."""
        payload: dict[str, Any] = {"selling_group_id": selling_group_id}
        if day_offset is not None:
            payload["day_offset"] = day_offset
        if portions is not None:
            payload["portions"] = portions
        return AssignSellingGroupToBasketResult.model_validate(
            obj=self._run_task(task="assign-selling-group-to-basket", payload=payload)
        )

    def update_selling_group_portions(self, selling_group_id: str, day_offset: int, portions: int) -> None:
        """Changes the number of portions of a recipe that is already in the basket."""
        self._run_task(
            task="update-selling-group-number-of-portions-task",
            payload={"selling_group_id": selling_group_id, "day_offset": day_offset, "portions": portions},
        )

    def remove_selling_group_from_basket(self, selling_group_id: str) -> RemoveSellingGroupFromBasketResult:
        """Removes a recipe from the basket."""
        return RemoveSellingGroupFromBasketResult.model_validate(
            obj=self._run_task(task="remove-selling-group-from-basket", payload={"selling_group_id": selling_group_id})
        )

    def get_user_defined_recipes(self) -> list[RecipeSummary]:
        """Lists the user's own recipes from the cookbook's `USER_DEFINED_RECIPES` segment."""
        return extract_recipes(page=self.get_cookbook_page(), segment_type="USER_DEFINED_RECIPES")

    def get_user_defined_recipe(
        self, recipe_id: str, portions: int | None = None, resolve_ingredient_names: bool = False
    ) -> RecipeDetails:
        """Returns the same structured details as `get_recipe` for one of the user's own recipes."""
        return self.get_recipe(
            recipe_id=recipe_id, portions=portions, resolve_ingredient_names=resolve_ingredient_names
        )

    def get_user_defined_recipe_image_selection_page(self, recipe_id: str) -> FusionPageLayout:
        """Returns the image selection page of a user defined recipe. This route returns a bare page layout."""
        return FusionPageLayout.model_validate(
            obj=self._http.send_request(
                method="GET",
                path=(
                    "/pages/sellable-image-selection-page-root"
                    f"?origin=RECIPE_DETAILS&sellable_id={quote(recipe_id, safe='')}"
                ),
                include_picnic_headers=True,
            )
        )

    def get_user_defined_recipe_suggested_images(self, recipe_id: str) -> list[UserDefinedRecipeSuggestedImage]:
        """Returns the suggested images for a user defined recipe."""
        page = self.get_user_defined_recipe_image_selection_page(recipe_id=recipe_id)
        return extract_suggested_images(page=page.raw())

    def create_user_defined_recipe(
        self, name: str, ingredients: list[NewUserDefinedRecipeIngredient], portions: int = 4
    ) -> CreateUserDefinedRecipeResult:
        """Creates a recipe of the user's own. The app limits names to 43 characters."""
        payload = {
            "name": name,
            "portions": portions,
            "selling_unit_quantities_by_id": {item.selling_unit_id: item.quantity for item in ingredients},
            "selling_unit_sources": {item.selling_unit_id: item.source for item in ingredients},
            "selling_units": [item.selling_unit_id for item in ingredients],
        }
        return CreateUserDefinedRecipeResult.model_validate(
            obj=self._run_task(task="create-user-defined-recipe", payload=payload)
        )

    def rename_user_defined_recipe(self, recipe_id: str, name: str) -> None:
        """Renames a user defined recipe. The app limits names to 43 characters."""
        self._run_task(task="update-name-user-defined-recipe", payload={"name": name, "selling_group_id": recipe_id})

    def update_user_defined_recipe_portions(self, recipe_id: str, portions: int) -> None:
        """Changes the default number of portions of a user defined recipe."""
        self._run_task(
            task="update-portions-user-defined-recipe", payload={"portions": portions, "sellable_id": recipe_id}
        )

    def delete_user_defined_recipe(self, recipe_id: str) -> None:
        """Deletes a user defined recipe. Call `remove_selling_group_from_basket` first to also empty the basket."""
        self._run_task(task="delete-user-defined-sellable", payload={"sellable_id": recipe_id})

    def add_user_defined_recipe_ingredient(
        self, recipe_id: str, selling_unit_id: str, quantity: int = 1, portions: int = 4, order: int = 0
    ) -> AddUserDefinedRecipeIngredientResult:
        """Adds a product (e.g. `s1143210`) as ingredient. `order` is its list position; numbers go as strings."""
        payload = {
            "order": str(order),
            "quantity": quantity,
            "requested_portions": str(portions),
            "selling_group_id": recipe_id,
            "selling_unit_id": selling_unit_id,
        }
        return AddUserDefinedRecipeIngredientResult.model_validate(
            obj=self._run_task(task="add-ingredient-task", payload=payload)
        )

    def update_user_defined_recipe_ingredient(
        self,
        recipe_id: str,
        ingredient_id: str,
        selling_unit_quantities: dict[str, int],
        portions: int = 4,
        swap_type: SellingGroupSwapType | None = None,
    ) -> UpdateUserDefinedRecipeIngredientResult:
        """Changes the quantity of an ingredient, or swaps its product by passing a different selling unit id.

        When swapping an ingredient with several selling units, include its current ones with quantity 0. When the
        result has `should_update_cart`, call `assign_sellable_component_to_day` with the same selection.
        `swap_type` is `WITHIN_SELLING_GROUP_COMPONENT`, `POPULAR_SELECTION` or `SEARCH_SELECTION`.
        """
        payload: dict[str, Any] = {
            "requested_sellable_portions": str(portions),
            "selling_group_component_id": ingredient_id,
            "selling_group_id": recipe_id,
            "selling_unit_quantity_by_id": selling_unit_quantities,
        }
        if swap_type is not None:
            payload["swapType"] = swap_type
        return UpdateUserDefinedRecipeIngredientResult.model_validate(
            obj=self._run_task(task="save-selling-group-edit-task", payload=payload)
        )

    def assign_sellable_component_to_day(
        self,
        recipe_id: str,
        ingredient_id: str,
        selling_unit_quantities: dict[str, int],
        portions: int,
        swap_type: SellingGroupSwapType,
    ) -> AssignSellableComponentToDayResult:
        """Pushes an updated ingredient selection of a recipe in the basket to the basket.

        Call it after `update_user_defined_recipe_ingredient` returned `should_update_cart`, with only the selected
        selling units (no zeroes). Without it the basket lacks that ingredient.
        """
        payload = {
            "component_swap_type": swap_type,
            "portions": str(portions),
            "required_amount_by_selling_unit_id": selling_unit_quantities,
            "selected_component_id": ingredient_id,
            "selling_group_id": recipe_id,
        }
        return AssignSellableComponentToDayResult.model_validate(
            obj=self._run_task(task="assign-sellable-component-to-day", payload=payload)
        )

    def remove_user_defined_recipe_ingredient(
        self, recipe_id: str, ingredient_id: str
    ) -> RemoveUserDefinedRecipeIngredientResult:
        """Removes an ingredient from a user defined recipe."""
        return RemoveUserDefinedRecipeIngredientResult.model_validate(
            obj=self._run_task(
                task="delete-selling-group-component",
                payload={"selling_group_component_id": ingredient_id, "selling_group_id": recipe_id},
            )
        )

    def set_user_defined_recipe_note(self, recipe_id: str, note: str) -> None:
        """Sets the HTML note of a user defined recipe (e.g. `<p>Kook de pasta.</p>`, at most 5000 characters)."""
        self._run_task(task="update-selling-group-note", payload={"note": note, "selling_group_id": recipe_id})

    def delete_user_defined_recipe_note(self, recipe_id: str) -> None:
        """Deletes the note of a user defined recipe."""
        self._run_task(task="delete-selling-group-note-task", payload={"selling_group_id": recipe_id})

    def upload_user_defined_recipe_image(
        self, recipe_id: str, data: bytes, content_type: str = "image/jpeg"
    ) -> UserDefinedRecipeImageUploadResult:
        """Uploads a photo as raw bytes; select the returned `image_id` with `select_user_defined_recipe_image`."""
        return UserDefinedRecipeImageUploadResult.model_validate(
            obj=self._http.send_request(
                method="POST",
                path=f"/user-defined-sellable/{quote(recipe_id, safe='')}",
                data=data,
                include_picnic_headers=True,
                content_type=JPG.sub("jpeg", content_type),
            )
        )

    def select_user_defined_recipe_image(
        self, recipe_id: str, image_id: str, reference_image: UserDefinedRecipeReferenceImage | None = None
    ) -> None:
        """Selects the image of a user defined recipe: a suggested image (with its `reference_image`) or an upload."""
        payload: dict[str, Any] = {"sellable_id": recipe_id, "selected_image_id": image_id}
        if reference_image is not None:
            payload["reference_image"] = reference_image.model_dump()
        self._run_task(task="select-sellable-image", payload=payload)

    def _get_page(self, path: str) -> FusionPage:
        return FusionPage.model_validate(
            obj=self._http.send_request(method="GET", path=path, include_picnic_headers=True)
        )

    def _run_task(self, task: str, payload: dict[str, Any]) -> Any:
        return self._http.send_request(
            method="POST", path=f"/pages/task/{task}", data={"payload": payload}, include_picnic_headers=True
        )

    def _get_recipe_details(self, recipe_id: str, portions: int | None) -> RecipeDetails:
        page = self.get_recipe_details_page(recipe_id=recipe_id, portions=portions)
        return extract_recipe_details(recipe_id=recipe_id, page=page)

    def _with_product_names(self, details: RecipeDetails) -> RecipeDetails:
        product_ids = list(
            dict.fromkeys(
                ingredient.selling_unit_id
                for ingredient in details.ingredients
                if ingredient.name is None and ingredient.selling_unit_id
            )
        )
        if not product_ids:
            return details

        catalog = CatalogService(http=self._http)
        with ThreadPoolExecutor() as pool:
            pages = pool.map(lambda product_id: catalog.get_product_details_page(product_id=product_id), product_ids)
            names = {
                product_id: extract_ingredient_product_name(page=page)
                for product_id, page in zip(product_ids, pages, strict=True)
            }
        ingredients = [
            ingredient.model_copy(update={"name": names[ingredient.selling_unit_id]})
            if ingredient.name is None and ingredient.selling_unit_id in names
            else ingredient
            for ingredient in details.ingredients
        ]
        return details.model_copy(update={"ingredients": ingredients})
