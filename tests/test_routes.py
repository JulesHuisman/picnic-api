"""Every service route: HTTP method, path, body, headers and the parsed return type."""

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import BaseModel

from picnic_api import PicnicClient
from picnic_api.domains.cart.models import (
    AddProductsItem,
    Cart,
    CheckoutConfirmation,
    CheckoutStatusResult,
    GetDeliverySlotsResult,
    InitiatePaymentResult,
    OrderStatus,
    RecipeContext,
    UserSlotMinimumOrderValue,
)
from picnic_api.domains.consent.models import (
    ConsentDeclaration,
    ConsentRequest,
    SetConsentSettingsInput,
    SetConsentSettingsResult,
    SetGeneralConsentsInput,
)
from picnic_api.domains.customer_service.models import (
    CustomerServiceContactInfo,
    MessagesWrapper,
    Reminder,
    RemindersWrapper,
)
from picnic_api.domains.delivery.models import DeliveryDetail, DeliveryPosition, DeliveryScenario
from picnic_api.domains.payment.models import PaymentProfile, WalletTransactionDetails
from picnic_api.domains.recipe.models import (
    AddUserDefinedRecipeIngredientResult,
    AssignSellableComponentToDayResult,
    AssignSellingGroupToBasketResult,
    RemoveSellingGroupFromBasketResult,
    RemoveUserDefinedRecipeIngredientResult,
)
from picnic_api.domains.user.models import ProfileMenu, UpdateCheckResult, User, UserInfo
from picnic_api.models.fusion import BootstrapData, FusionPage, PmlDocument
from tests import samples
from tests.conftest import BASE_URL, MockApi

NO_BODY = object()
DECLARATION = ConsentDeclaration(consent_request_text_id="text-1", consent_request_locale="nl", agreement=True)
CHECKOUT_START = {
    "order_id": "order-1",
    "total_price": 865,
    "total_count": 1,
    "total_deposit": 25,
    "total_savings": 0,
    "transaction_expiry": "2026-10-02T12:00:00Z",
    "delivery_slots": [samples.DELIVERY_SLOT],
    "deposit_breakdown": [],
}

type Call = Callable[[PicnicClient], Any]

ROUTES: list[tuple[str, Call, Any, str, str, Any, bool, type | None]] = [
    ("bootstrap", lambda c: c.app.get_bootstrap_data(), samples.BOOTSTRAP, "GET", "/bootstrap", NO_BODY, False, BootstrapData),
    ("deeplink", lambda c: c.app.resolve_deeplink(url="https://picnic.app/nl/deeplink/x"), {"url": "picnic://x"}, "POST", "/deeplink/resolve", {"url": "https://picnic.app/nl/deeplink/x"}, True, None),
    ("2fa generate", lambda c: c.auth.generate_2fa_code(channel="SMS"), None, "POST", "/user/2fa/generate", {"channel": "SMS"}, True, None),
    ("logout", lambda c: c.auth.logout(), None, "POST", "/user/logout", NO_BODY, False, None),
    ("phone generate", lambda c: c.auth.generate_phone_verification_code(phone_number="+316"), None, "POST", "/user/phone_verification/generate", {"phone_number": "+316"}, False, None),
    ("phone verify", lambda c: c.auth.verify_phone_number(phone_number="+316", code="1234"), None, "POST", "/user/phone_verification/verify", {"otp": "1234", "phone_number": "+316"}, False, None),
    ("get cart", lambda c: c.cart.get_cart(), samples.CART, "GET", "/cart", NO_BODY, True, Cart),
    ("add product", lambda c: c.cart.add_product_to_cart(product_id="s1", count=2), samples.CART, "POST", "/cart/add_product", {"product_id": "s1", "count": 2}, True, Cart),
    ("add product with context", lambda c: c.cart.add_product_to_cart(product_id="s1", selling_unit_contexts=[RecipeContext(recipe_id="r1")]), samples.CART, "POST", "/cart/add_product", {"product_id": "s1", "count": 1, "selling_unit_contexts": [{"type": "RECIPE", "recipe_id": "r1"}]}, True, Cart),
    ("add products", lambda c: c.cart.add_products_to_cart(products=[AddProductsItem(product_id="s11295810", quantity=2), AddProductsItem(product_id="s10000123", quantity=1)]), samples.CART, "POST", "/cart/products/add", {"s11295810": 2, "s10000123": 1}, True, Cart),
    ("remove product", lambda c: c.cart.remove_product_from_cart(product_id="s1"), samples.CART, "POST", "/cart/remove_product", {"product_id": "s1", "count": 1}, True, Cart),
    ("clear cart", lambda c: c.cart.clear_cart(), samples.CART, "POST", "/cart/clear", NO_BODY, True, Cart),
    ("delivery slots", lambda c: c.cart.get_delivery_slots(), {"delivery_slots": [samples.DELIVERY_SLOT], "slot_selector_message": samples.PML, "selected_slot": {"slot_id": "slot-1", "state": "IMPLICIT"}}, "GET", "/cart/delivery_slots", NO_BODY, False, GetDeliverySlotsResult),
    ("set slot", lambda c: c.cart.set_delivery_slot(slot_id="slot-1"), samples.CART, "POST", "/cart/set_delivery_slot", {"slot_id": "slot-1"}, True, Cart),
    ("order status", lambda c: c.cart.get_order_status(order_id="order-1"), {"checkout_status": "FINISHED"}, "GET", "/cart/checkout/order/order-1/status", NO_BODY, False, OrderStatus),
    ("remove group", lambda c: c.cart.remove_group_from_cart(group_id="group-1"), samples.CART, "POST", "/cart/remove_group", {"group_id": "group-1"}, True, Cart),
    ("minimum order value", lambda c: c.cart.get_minimum_order_value(), {"slot_id": "slot-1", "minimum_order_value": 3500}, "GET", "/user-slot-minimum-order-value/minimum", NO_BODY, True, UserSlotMinimumOrderValue),
    ("confirm order", lambda c: c.cart.confirm_order(order_id="order-1"), {"order_id": "order-1", "delivery_slot": samples.DELIVERY_SLOT, "analytics": None}, "POST", "/cart/checkout/order/order-1/confirm", NO_BODY, False, CheckoutConfirmation),
    ("start checkout", lambda c: c.cart.start_checkout(mts=1234567890), CHECKOUT_START, "POST", "/cart/checkout/start", {"mts": 1234567890, "oos_article_ids": None}, True, None),
    ("start checkout resolved", lambda c: c.cart.start_checkout(mts=1, oos_article_ids=["a"], resolve_key="age_verified"), CHECKOUT_START, "POST", "/cart/checkout/start", {"mts": 1, "oos_article_ids": ["a"], "resolve_key": "age_verified"}, True, None),
    ("initiate payment", lambda c: c.cart.initiate_payment(order_id="order-1", app_return_url="https://example.com/return"), {"payment_id": "pay-1", "transaction_id": "tx-1", "action": {"type": "redirect", "redirect_url": "https://bank.example/pay"}}, "POST", "/cart/checkout/initiate_payment", {"order_id": "order-1", "app_return_url": "https://example.com/return"}, True, InitiatePaymentResult),
    ("checkout status", lambda c: c.cart.get_checkout_status(transaction_id="tx-1"), {"checkout_status": "PENDING"}, "GET", "/cart/checkout/tx-1/status", NO_BODY, False, CheckoutStatusResult),
    ("cancel checkout", lambda c: c.cart.cancel_checkout(transaction_id="tx-1"), None, "POST", "/cart/checkout/cancel", {"transaction_id": "tx-1"}, True, None),
    ("suggestions", lambda c: c.catalog.get_suggestions(query="kaas & wijn"), [{"type": "SEARCH_SUGGESTION", "id": "1", "suggestion": "kaas"}], "GET", "/suggest?search_term=kaas%20%26%20wijn", NO_BODY, False, list),
    ("product page", lambda c: c.catalog.get_product_details_page(product_id="s1001524"), samples.FUSION_PAGE, "GET", "/pages/product-details-page-root?id=s1001524&show_category_action=true&show_remove_from_purchases_page_action=true", NO_BODY, True, FusionPage),
    ("consent settings", lambda c: c.consent.get_consent_settings(), [samples.CONSENT_SETTING], "GET", "/consents/settings-page", NO_BODY, False, list),
    ("general consent settings", lambda c: c.consent.get_consent_settings(general=True), [samples.CONSENT_SETTING], "GET", "/consents/general/settings-page", NO_BODY, False, list),
    ("set consents", lambda c: c.consent.set_consent_settings(consent_settings=SetConsentSettingsInput(consent_declarations=[DECLARATION])), {"consent_request_text_ids": ["text-1"]}, "PUT", "/consents", {"consent_declarations": [DECLARATION.model_dump()]}, False, SetConsentSettingsResult),
    ("get consents", lambda c: c.consent.get_consents(consent_topics=["MISC_COMMERCIAL_ADS", "MISC_READ_ADVERTISING_ID"], strategy="WIDE"), [samples.CONSENT_REQUEST], "GET", "/consents?consent_topics=MISC_COMMERCIAL_ADS&consent_topics=MISC_READ_ADVERTISING_ID&strategy=WIDE", NO_BODY, False, list),
    ("general consents", lambda c: c.consent.get_general_consents(), samples.CONSENT_REQUEST, "GET", "/consents/general", NO_BODY, False, ConsentRequest),
    ("set general consents", lambda c: c.consent.set_general_consents(declarations=SetGeneralConsentsInput(consent_declarations=[DECLARATION], general_consent=True)), None, "PUT", "/consents/general", {"consent_declarations": [DECLARATION.model_dump()], "general_consent": True}, False, None),
    ("faq", lambda c: c.content.get_faq_content(), samples.PML, "GET", "/content/faq", NO_BODY, True, PmlDocument),
    ("search empty state", lambda c: c.content.get_search_empty_state(), samples.PML, "GET", "/content/search_empty_state", NO_BODY, True, PmlDocument),
    ("contact info", lambda c: c.customer_service.get_contact_info(), samples.CONTACT_INFO, "GET", "/cs-contact-info", NO_BODY, True, CustomerServiceContactInfo),
    ("messages", lambda c: c.customer_service.get_messages(), samples.MESSAGES, "GET", "/messages", NO_BODY, True, MessagesWrapper),
    ("filtered messages", lambda c: c.customer_service.get_messages(display_positions=["PROMPT", "MESSAGE_BAR"]), samples.MESSAGES, "GET", "/messages?display_position=PROMPT&display_position=MESSAGE_BAR", NO_BODY, True, MessagesWrapper),
    ("reminders", lambda c: c.customer_service.get_reminders(), {"reminders": [{"day_of_week": "MONDAY", "time_of_day": [8, 0]}]}, "GET", "/reminders", NO_BODY, True, RemindersWrapper),
    ("set reminders", lambda c: c.customer_service.set_reminders(reminders=[Reminder(day_of_week="FRIDAY", time_of_day=[9, 30])]), None, "PUT", "/reminders", [{"day_of_week": "FRIDAY", "time_of_day": [9, 30]}], True, None),
    ("parcels", lambda c: c.customer_service.get_parcels(), [samples.PARCEL], "GET", "/parcels", NO_BODY, True, list),
    ("deliveries", lambda c: c.delivery.get_deliveries(), [samples.DELIVERY], "POST", "/deliveries/summary", [], False, list),
    ("filtered deliveries", lambda c: c.delivery.get_deliveries(statuses=["CURRENT"]), [samples.DELIVERY], "POST", "/deliveries/summary", ["CURRENT"], False, list),
    ("delivery", lambda c: c.delivery.get_delivery(delivery_id="delivery-1"), samples.DELIVERY_DETAIL, "GET", "/deliveries/delivery-1", NO_BODY, False, DeliveryDetail),
    ("delivery position", lambda c: c.delivery.get_delivery_position(delivery_id="delivery-1"), samples.DELIVERY_POSITION, "GET", "/deliveries/delivery-1/position", NO_BODY, True, DeliveryPosition),
    ("delivery scenario", lambda c: c.delivery.get_delivery_scenario(delivery_id="delivery-1"), samples.DELIVERY_SCENARIO, "GET", "/deliveries/delivery-1/scenario", NO_BODY, True, DeliveryScenario),
    ("cancel delivery", lambda c: c.delivery.cancel_delivery(delivery_id="delivery-1"), {}, "POST", "/order/delivery/delivery-1/cancel", NO_BODY, False, dict),
    ("rate delivery", lambda c: c.delivery.set_delivery_rating(delivery_id="delivery-1", rating=10), "OK", "POST", "/deliveries/delivery-1/rating", {"rating": 10}, False, str),
    ("invoice email", lambda c: c.delivery.send_delivery_invoice_email(delivery_id="delivery-1"), "OK", "POST", "/deliveries/delivery-1/resend_invoice_email", NO_BODY, False, str),
    ("payment profile", lambda c: c.payment.get_payment_profile(), samples.PAYMENT_PROFILE, "GET", "/payment-profile", NO_BODY, True, PaymentProfile),
    ("wallet transactions", lambda c: c.payment.get_wallet_transactions(page_number=1), [samples.WALLET_TRANSACTION], "POST", "/wallet/transactions", {"page_number": 1}, False, list),
    ("wallet transaction", lambda c: c.payment.get_wallet_transaction_details(wallet_transaction_id="tx-1"), samples.WALLET_TRANSACTION_DETAILS, "GET", "/wallet/transactions/tx-1", NO_BODY, False, WalletTransactionDetails),
    ("user", lambda c: c.user.get_user_details(), samples.USER, "GET", "/user", NO_BODY, False, User),
    ("user info", lambda c: c.user.get_user_info(), samples.USER_INFO, "GET", "/user-info", NO_BODY, False, UserInfo),
    ("profile menu", lambda c: c.user.get_profile_menu(), samples.PROFILE_MENU, "GET", "/profile-menu?fetch_mgm=true", NO_BODY, True, ProfileMenu),
    ("suggestion", lambda c: c.user.submit_suggestion(suggestion="More cheese"), None, "POST", "/user/suggestion", {"suggestion": "More cheese"}, False, None),
    ("push token", lambda c: c.user.register_push_token(push_token="token", platform="firebase"), None, "POST", "/user/device/register_push", {"push_token": "token", "platform": "firebase"}, False, None),
    ("update check", lambda c: c.user.check_for_updates(), samples.UPDATE_CHECK, "POST", "/update_check", {"device_id": "3C417201548B2E3B", "device_name": "notAvailable", "client_id": "30100", "version": "1.246.1", "device_os": "30100;1.246.1-15599;", "build_number": "15599"}, True, UpdateCheckResult),
    ("household", lambda c: c.user_onboarding.set_household_details(details={"adults": 2}), None, "POST", "/user-onboarding/household-details", {"adults": 2}, False, None),
    ("business", lambda c: c.user_onboarding.set_business_details(details={"sector": "IT"}), None, "POST", "/user-onboarding/business-details", {"sector": "IT"}, False, None),
    ("subscribe push", lambda c: c.user_onboarding.subscribe_push(topics=["deals"]), None, "POST", "/user-onboarding/subscribe-push", {"topics": ["deals"]}, False, None),
    ("meals page", lambda c: c.recipe.get_recipes_page(), samples.FUSION_PAGE, "GET", "/pages/meals-page-root", NO_BODY, True, FusionPage),
    ("cookbook page", lambda c: c.recipe.get_cookbook_page(), samples.FUSION_PAGE, "GET", "/pages/cookbook-page-content", NO_BODY, True, FusionPage),
    ("recipe page", lambda c: c.recipe.get_recipe_details_page(recipe_id="0123456789abcdef01234567"), samples.FUSION_PAGE, "GET", "/pages/selling-group-details-page?selling_group_id=0123456789abcdef01234567", NO_BODY, True, FusionPage),
    ("recipe page portions", lambda c: c.recipe.get_recipe_details_page(recipe_id="r1", portions=2), samples.FUSION_PAGE, "GET", "/pages/selling-group-details-page?selling_group_id=r1&portions=2", NO_BODY, True, FusionPage),
    ("unsave recipe", lambda c: c.recipe.unsave_recipe(recipe_id="r1"), {}, "POST", "/pages/task/recipe-saving", {"payload": {"recipe_id": "r1", "saved_at": None}}, True, None),
    ("assign selling group", lambda c: c.recipe.assign_selling_group_to_basket(selling_group_id="r1", day_offset=1, portions=2), {"anyUnavailableIngredient": False, "assignedNumberOfPortions": 2, "cart": samples.SELLING_GROUP_CART}, "POST", "/pages/task/assign-selling-group-to-basket", {"payload": {"selling_group_id": "r1", "day_offset": 1, "portions": 2}}, True, AssignSellingGroupToBasketResult),
    ("assign selling group defaults", lambda c: c.recipe.assign_selling_group_to_basket(selling_group_id="r1"), {"anyUnavailableIngredient": False, "assignedNumberOfPortions": 4, "cart": samples.SELLING_GROUP_CART}, "POST", "/pages/task/assign-selling-group-to-basket", {"payload": {"selling_group_id": "r1"}}, True, AssignSellingGroupToBasketResult),
    ("update portions", lambda c: c.recipe.update_selling_group_portions(selling_group_id="r1", day_offset=0, portions=6), {}, "POST", "/pages/task/update-selling-group-number-of-portions-task", {"payload": {"selling_group_id": "r1", "day_offset": 0, "portions": 6}}, True, None),
    ("remove selling group", lambda c: c.recipe.remove_selling_group_from_basket(selling_group_id="r1"), {"cart": samples.SELLING_GROUP_CART, "selectedSellableComponentIds": ["c1"], "SURemoved": [{"quantity": 1, "selling_unit_id": "s1"}]}, "POST", "/pages/task/remove-selling-group-from-basket", {"payload": {"selling_group_id": "r1"}}, True, RemoveSellingGroupFromBasketResult),
    ("rename udr", lambda c: c.recipe.rename_user_defined_recipe(recipe_id="r1", name="Nieuwe naam"), {}, "POST", "/pages/task/update-name-user-defined-recipe", {"payload": {"name": "Nieuwe naam", "selling_group_id": "r1"}}, True, None),
    ("udr portions", lambda c: c.recipe.update_user_defined_recipe_portions(recipe_id="r1", portions=6), {}, "POST", "/pages/task/update-portions-user-defined-recipe", {"payload": {"portions": 6, "sellable_id": "r1"}}, True, None),
    ("delete udr", lambda c: c.recipe.delete_user_defined_recipe(recipe_id="r1"), {}, "POST", "/pages/task/delete-user-defined-sellable", {"payload": {"sellable_id": "r1"}}, True, None),
    ("add ingredient", lambda c: c.recipe.add_user_defined_recipe_ingredient(recipe_id="r1", selling_unit_id="s1010706", quantity=1, portions=4, order=7), {"newComponentId": "c1"}, "POST", "/pages/task/add-ingredient-task", {"payload": {"order": "7", "quantity": 1, "requested_portions": "4", "selling_group_id": "r1", "selling_unit_id": "s1010706"}}, True, AddUserDefinedRecipeIngredientResult),
    ("assign component", lambda c: c.recipe.assign_sellable_component_to_day(recipe_id="r1", ingredient_id="c1", selling_unit_quantities={"s1189145": 1}, portions=2, swap_type="SEARCH_SELECTION"), {"cart": samples.SELLING_GROUP_CART}, "POST", "/pages/task/assign-sellable-component-to-day", {"payload": {"component_swap_type": "SEARCH_SELECTION", "portions": "2", "required_amount_by_selling_unit_id": {"s1189145": 1}, "selected_component_id": "c1", "selling_group_id": "r1"}}, True, AssignSellableComponentToDayResult),
    ("remove ingredient", lambda c: c.recipe.remove_user_defined_recipe_ingredient(recipe_id="r1", ingredient_id="c1"), {}, "POST", "/pages/task/delete-selling-group-component", {"payload": {"selling_group_component_id": "c1", "selling_group_id": "r1"}}, True, RemoveUserDefinedRecipeIngredientResult),
    ("set note", lambda c: c.recipe.set_user_defined_recipe_note(recipe_id="r1", note="<p>Kook de pasta.</p>"), {}, "POST", "/pages/task/update-selling-group-note", {"payload": {"note": "<p>Kook de pasta.</p>", "selling_group_id": "r1"}}, True, None),
    ("delete note", lambda c: c.recipe.delete_user_defined_recipe_note(recipe_id="r1"), {}, "POST", "/pages/task/delete-selling-group-note-task", {"payload": {"selling_group_id": "r1"}}, True, None),
    ("select image", lambda c: c.recipe.select_user_defined_recipe_image(recipe_id="r1", image_id="img-1"), {}, "POST", "/pages/task/select-sellable-image", {"payload": {"sellable_id": "r1", "selected_image_id": "img-1"}}, True, None),
]  # fmt: skip


@pytest.mark.parametrize(
    argnames=("call", "reply", "method", "path", "body", "picnic_headers", "returns"),
    argvalues=[pytest.param(*route[1:], id=route[0]) for route in ROUTES],
)
def test_route(
    client: PicnicClient,
    api: MockApi,
    call: Call,
    reply: Any,
    method: str,
    path: str,
    body: Any,
    picnic_headers: bool,
    returns: type | None,
) -> None:
    if reply is not None:
        api.queue_json(reply)

    result = call(client)

    request = api.last
    assert request.method == method
    assert str(request.url) == f"{BASE_URL}{path}"
    assert request.headers["x-picnic-auth"] == "initial-auth-key"
    assert ("x-picnic-agent" in request.headers) is picnic_headers
    assert ("x-picnic-did" in request.headers) is picnic_headers
    if body is NO_BODY:
        assert request.content == b""
    else:
        assert api.last_json() == body
    if returns is not None:
        assert isinstance(result, returns)
    if isinstance(result, list):
        assert result and all(isinstance(item, BaseModel) for item in result)
