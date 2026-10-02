from typing import Any

from picnic_api.domains.cart.models import (
    AddProductsItem,
    Cart,
    CheckoutConfirmation,
    CheckoutStartResult,
    CheckoutStatusResult,
    GetDeliverySlotsResult,
    InitiatePaymentResult,
    OrderStatus,
    SellingUnitContext,
    UserSlotMinimumOrderValue,
)
from picnic_api.http_client import HttpClient


class CartService:
    """Cart management, delivery slots and checkout."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def get_cart(self) -> Cart:
        """Returns the cart of the current user."""
        return Cart.model_validate(self._http.send_request(method="GET", path="/cart", include_picnic_headers=True))

    def add_product_to_cart(
        self, product_id: str, count: int = 1, selling_unit_contexts: list[SellingUnitContext] | None = None
    ) -> Cart:
        """Adds `count` of a product to the cart. `selling_unit_contexts` track the origin (e.g. recipe, meal plan)."""
        return self._mutate_product(
            path="/cart/add_product", product_id=product_id, count=count, selling_unit_contexts=selling_unit_contexts
        )

    def add_products_to_cart(self, products: list[AddProductsItem]) -> Cart:
        """Adds multiple products to the cart in a single request."""
        body = {product.product_id: product.quantity for product in products}
        return Cart.model_validate(
            self._http.send_request(method="POST", path="/cart/products/add", data=body, include_picnic_headers=True)
        )

    def remove_product_from_cart(
        self, product_id: str, count: int = 1, selling_unit_contexts: list[SellingUnitContext] | None = None
    ) -> Cart:
        """Removes `count` of a product from the cart."""
        return self._mutate_product(
            path="/cart/remove_product",
            product_id=product_id,
            count=count,
            selling_unit_contexts=selling_unit_contexts,
        )

    def clear_cart(self) -> Cart:
        """Removes all items from the cart."""
        return Cart.model_validate(
            self._http.send_request(method="POST", path="/cart/clear", include_picnic_headers=True)
        )

    def get_delivery_slots(self) -> GetDeliverySlotsResult:
        """Returns all available delivery slots."""
        return GetDeliverySlotsResult.model_validate(self._http.send_request(method="GET", path="/cart/delivery_slots"))

    def set_delivery_slot(self, slot_id: str) -> Cart:
        """Selects a delivery slot."""
        return Cart.model_validate(
            self._http.send_request(
                method="POST", path="/cart/set_delivery_slot", data={"slot_id": slot_id}, include_picnic_headers=True
            )
        )

    def get_order_status(self, order_id: str) -> OrderStatus:
        """Returns the status of an order (not a delivery)."""
        return OrderStatus.model_validate(
            self._http.send_request(method="GET", path=f"/cart/checkout/order/{order_id}/status")
        )

    def remove_group_from_cart(self, group_id: str) -> Cart:
        """Removes an entire group of products from the cart at once."""
        return Cart.model_validate(
            self._http.send_request(
                method="POST", path="/cart/remove_group", data={"group_id": group_id}, include_picnic_headers=True
            )
        )

    def get_minimum_order_value(self) -> UserSlotMinimumOrderValue:
        """Returns the minimum order value for the selected delivery slot. The API answers 500 without a slot."""
        return UserSlotMinimumOrderValue.model_validate(
            self._http.send_request(
                method="GET", path="/user-slot-minimum-order-value/minimum", include_picnic_headers=True
            )
        )

    def confirm_order(self, order_id: str) -> CheckoutConfirmation:
        """Confirms and places an order."""
        return CheckoutConfirmation.model_validate(
            self._http.send_request(method="POST", path=f"/cart/checkout/order/{order_id}/confirm")
        )

    def start_checkout(
        self, mts: int, oos_article_ids: list[str] | None = None, resolve_key: str | None = None
    ) -> CheckoutStartResult:
        """Starts the checkout for the current cart. `mts` must match the cart's modification timestamp.

        Raises `CheckoutIssueError` when the cart has issues; retry with its `resolve_key` for the age check.
        """
        body: dict[str, Any] = {"mts": mts, "oos_article_ids": oos_article_ids}
        if resolve_key:
            body["resolve_key"] = resolve_key
        return CheckoutStartResult.model_validate(
            self._http.send_request(method="POST", path="/cart/checkout/start", data=body, include_picnic_headers=True)
        )

    def initiate_payment(self, order_id: str, app_return_url: str) -> InitiatePaymentResult:
        """Initiates payment for a checkout order and returns the bank redirect."""
        return InitiatePaymentResult.model_validate(
            self._http.send_request(
                method="POST",
                path="/cart/checkout/initiate_payment",
                data={"order_id": order_id, "app_return_url": app_return_url},
                include_picnic_headers=True,
            )
        )

    def get_checkout_status(self, transaction_id: str) -> CheckoutStatusResult:
        """Returns the payment status of an in-progress checkout transaction."""
        return CheckoutStatusResult.model_validate(
            self._http.send_request(method="GET", path=f"/cart/checkout/{transaction_id}/status")
        )

    def cancel_checkout(self, transaction_id: str) -> None:
        """Cancels an in-progress checkout transaction."""
        self._http.send_request(
            method="POST",
            path="/cart/checkout/cancel",
            data={"transaction_id": transaction_id},
            include_picnic_headers=True,
        )

    def _mutate_product(
        self, path: str, product_id: str, count: int, selling_unit_contexts: list[SellingUnitContext] | None
    ) -> Cart:
        body: dict[str, Any] = {"product_id": product_id, "count": count}
        if selling_unit_contexts is not None:
            body["selling_unit_contexts"] = [context.model_dump(exclude_none=True) for context in selling_unit_contexts]
        return Cart.model_validate(
            self._http.send_request(method="POST", path=path, data=body, include_picnic_headers=True)
        )
