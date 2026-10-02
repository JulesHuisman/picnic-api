"""Recipe models.

Recipes are "selling groups". The user's own recipes are "user defined recipes" (UDR): selling groups with
`creator_type: "USER"` and a 32-hex-character id. Their task routes and payloads were extracted from the PML
expressions of the recipe pages (`user-defined-recipe-root`, `selling-group-details-page`,
`selling-group-component-edit-page`, `sellable-image-selection-page-root` and others).
"""

from typing import Annotated, Any, Literal

from pydantic import AliasChoices, Field

from picnic_api.models.common import CamelModel, PicnicModel

type RecipeSegment = Literal["SAVED_RECIPES", "USER_DEFINED_RECIPES"]

type SellingGroupSwapType = Literal["WITHIN_SELLING_GROUP_COMPONENT", "POPULAR_SELECTION", "SEARCH_SELECTION"]


class RecipeSummary(PicnicModel):
    """A catalog or user-defined recipe as listed in the cookbook.

    `image_type` comes from tile analytics (e.g. `COMPOSED`, `CUSTOM`, `SUGGESTED`, `GALLERY`) and may differ
    from `RecipeDetails.image_type`, which should be preferred.
    """

    id: str
    name: str
    image_type: str | None


class RecipeIngredient(PicnicModel):
    """One ingredient (selling group component) of a recipe.

    `selling_unit_id` is empty for some discontinued products. `quantity` is a selling-unit count for
    `RecipeDetails.portions`, not a weight. `checked` tells whether it is selected when adding the recipe to the
    basket.
    """

    ingredient_id: str
    name: str | None
    selling_unit_id: str
    quantity: int
    status: str
    swap_type: str | None
    checked: bool


class RecipeDetails(RecipeSummary):
    """Structured details of a catalog or user-defined recipe.

    `portions` (equal to `displayed_portions`) is the count the products and quantities are for, while
    `default_portions` is the stored default. `image_id` includes its namespace (e.g. `recipes/abc`). `note` is
    the user's HTML note, not the cooking steps of a catalog recipe.
    """

    portions: int
    default_portions: int
    displayed_portions: int
    creator_type: str
    is_recipe_owner: bool
    is_saved: bool
    image_id: str | None
    ingredients: list[RecipeIngredient]
    note: str | None


class NewUserDefinedRecipeIngredient(PicnicModel):
    """An ingredient for a new user defined recipe. `source` is analytics only (e.g. `usuals-suggestion`)."""

    selling_unit_id: str
    quantity: int = 1
    source: str = "search"


class CreateUserDefinedRecipeResult(CamelModel):
    selling_group_id: str
    modify_response: Any = None
    su_analytics: Any = Field(default=None, alias="SUAnalytics")


class AddUserDefinedRecipeIngredientResult(CamelModel):
    new_component_id: str


class SellingGroupLineDetail(CamelModel):
    type: Literal["SELLING_GROUP"]
    selling_group_id: str
    selling_group_component_id: str
    selling_group_component_type: str
    selling_group_component_swap_type: str | None


class MealPlanLineDetail(CamelModel):
    type: Literal["MEAL_PLAN"]
    day_relative_to_slot: int
    number_of_servings: int


class UnknownLineDetail(CamelModel):
    type: str


type CartLineDetail = Annotated[
    SellingGroupLineDetail | MealPlanLineDetail | UnknownLineDetail, Field(union_mode="left_to_right")
]


class SellingGroupCartLineContext(CamelModel):
    """A basket line's link to the recipe it was added for."""

    quantity: int
    details: list[CartLineDetail]


class AvailabilityStatus(CamelModel):
    type: str


class SellingGroupCartLine(CamelModel):
    availability_status: AvailabilityStatus
    quantity: int
    contexts: list[SellingGroupCartLineContext] | None = None


class SellingGroupCartSnapshot(CamelModel):
    """Basket snapshot returned by the recipe basket tasks, with lines keyed by selling unit id."""

    checkout_total_price: int | None
    generated_at: int
    selling_units: dict[str, SellingGroupCartLine]
    selling_units_total_price: int


class AssignSellingGroupToBasketResult(CamelModel):
    any_unavailable_ingredient: bool
    assigned_number_of_portions: int
    cart: SellingGroupCartSnapshot


class RemovedSellingUnit(PicnicModel):
    quantity: int
    selling_unit_id: str


class RemoveSellingGroupFromBasketResult(CamelModel):
    cart: SellingGroupCartSnapshot
    selected_sellable_component_ids: list[str]
    su_removed: list[RemovedSellingUnit] = Field(alias="SURemoved")


class UpdateUserDefinedRecipeIngredientResult(CamelModel):
    """`should_update_cart` means the basket still holds the old selection; see `assign_sellable_component_to_day`."""

    cart: SellingGroupCartSnapshot | None = None
    should_update_cart: bool | None = None


class AssignSellableComponentToDayResult(CamelModel):
    cart: SellingGroupCartSnapshot | None = None


class RemoveUserDefinedRecipeIngredientResult(CamelModel):
    cart: SellingGroupCartSnapshot | None = None


class UserDefinedRecipeReferenceImage(PicnicModel):
    """Metadata of a suggested recipe image. `sellable_id` is the Picnic recipe the image belongs to."""

    id: str
    namespace: str
    primary_image: bool
    rank_value: int
    sellable_id: str
    type: str


class UserDefinedRecipeSuggestedImage(PicnicModel):
    """A suggested image. Pass `id` and `reference_image` to `select_user_defined_recipe_image`."""

    id: str
    reference_image: UserDefinedRecipeReferenceImage


class UserDefinedRecipeImageUploadResult(PicnicModel):
    image_id: str | None = Field(default=None, validation_alias=AliasChoices("image_id", "imageId"))
    namespace: str | None = None
