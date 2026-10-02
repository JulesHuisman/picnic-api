from typing import Annotated, Any, Literal

from pydantic import Field

from picnic_api.models.common import Decorator, PicnicModel
from picnic_api.models.fusion import PmlDocument, PriceRange

type DeliveryStatus = str


class DeliverySlot(PicnicModel):
    slot_id: str
    hub_id: str
    fc_id: str
    window_start: str
    window_end: str
    cut_off_time: str
    is_available: bool
    selected: bool
    reserved: bool
    minimum_order_value: int | None = None
    unavailability_reason: str | None = None
    icon: PmlDocument | None = None
    slot_characteristics: list[str]


class SelectedSlot(PicnicModel):
    slot_id: str
    state: str


class OrderArticle(PicnicModel):
    type: Literal["ORDER_ARTICLE"]
    id: str
    name: str
    unit_quantity: str
    unit_quantity_sub: str | None = None
    price: int
    price_ranges: list[PriceRange] | None = None
    decorators: list[Decorator]
    max_count: int
    image_ids: list[str]
    perishable: bool
    analytics_contexts: list[Any]
    selling_unit_contexts_for_mutations: list[Any]


class OrderLine(PicnicModel):
    type: Literal["ORDER_LINE"]
    id: str
    items: list[OrderArticle]
    display_price: int
    price: int
    decorators: list[Decorator] | None = None


class DepositBreakdown(PicnicModel):
    type: str
    value: int
    count: int


class TransactionInfo(PicnicModel):
    bank_id: str
    payment_type: str
    redacted_iban: str
    refund_account: bool


class CartAnalyticsItem(PicnicModel):
    product_id: str
    quantity: int
    is_available: bool
    is_in_recipe: bool


class CartAnalyticsContextData(PicnicModel):
    items_list: list[CartAnalyticsItem]


class Cart(PicnicModel):
    """The active shopping cart returned by `GET /cart`, distinct from a placed `Order`."""

    type: Literal["ORDER"]
    id: str
    items: list[OrderLine]
    delivery_slots: list[DeliverySlot]
    selected_slot: SelectedSlot
    slot_selector_message: PmlDocument | None
    total_count: int
    total_price: int
    checkout_total_price: int
    total_savings: int | None = None
    mts: int
    deposit_breakdown: list[DepositBreakdown]
    decorator_overrides: dict[str, list[Decorator]]
    state_token: str
    fees: list[Any]
    basket_sections: list[Any]
    analytics_context_data: CartAnalyticsContextData
    show_create_sellable_banner: bool
    membership_savings: int


class Order(PicnicModel):
    """A placed order that is part of a delivery."""

    type: Literal["ORDER"]
    id: str
    items: list[OrderLine]
    total_price: int
    checkout_total_price: int
    total_savings: int
    total_deposit: int
    cancellable: bool
    creation_time: str
    status: DeliveryStatus
    decorator_overrides: dict[str, list[Decorator]]
    cancellation_time: str | None
    transaction_info: TransactionInfo | None = None
    slot_selector_message: PmlDocument | None = None
    deposit_breakdown: list[DepositBreakdown] | None = None
    fees: list[Any] | None = None
    basket_sections: list[Any] | None = None
    analytics_context_data: dict[str, Any] | None = None
    membership_savings: int | None = None


class MealPlanContext(PicnicModel):
    type: Literal["MEAL_PLAN"] = "MEAL_PLAN"
    day_offset: int
    servings: int


class SellingGroupContext(PicnicModel):
    type: Literal["SELLING_GROUP"] = "SELLING_GROUP"
    recipe_id: str
    ingredient_id: str
    component_type: str


class RecipeContext(PicnicModel):
    type: Literal["RECIPE", "RECIPES"] = "RECIPE"
    recipe_id: str
    section_id: str | None = None
    recipe_section_id: str | None = None
    recipe_ingredient_type: str | None = None


type SellingUnitContext = Annotated[MealPlanContext | SellingGroupContext | RecipeContext, Field(discriminator="type")]


class AddProductsItem(PicnicModel):
    product_id: str
    quantity: int


class GetDeliverySlotsResult(PicnicModel):
    delivery_slots: list[DeliverySlot]
    slot_selector_message: PmlDocument | None
    selected_slot: SelectedSlot


class OrderStatus(PicnicModel):
    checkout_status: str


class UserSlotMinimumOrderValue(PicnicModel):
    slot_id: str
    minimum_order_value: int


class CheckoutConfirmation(PicnicModel):
    order_id: str
    delivery_slot: DeliverySlot
    analytics: dict[str, Any] | None


class CheckoutAddress(PicnicModel):
    street: str | None = None
    city: str | None = None
    postcode: str | None = None
    house_number: int | None = None


class CheckoutStartResult(PicnicModel):
    order_id: str
    total_price: int
    total_count: int
    total_deposit: int
    total_savings: int
    transaction_expiry: str
    delivery_slots: list[DeliverySlot]
    deposit_breakdown: list[DepositBreakdown]
    address: CheckoutAddress | None = None


class PaymentAction(PicnicModel):
    type: str
    redirect_url: str


class InitiatePaymentResult(PicnicModel):
    payment_id: str
    transaction_id: str
    issuer_authentication_url: str | None = None
    action: PaymentAction


class CheckoutStatusResult(PicnicModel):
    checkout_status: str
