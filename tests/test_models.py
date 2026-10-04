from picnic_api.domains.cart.models import Cart, MealPlanContext, SellingGroupContext
from picnic_api.domains.consent.models import ConsentRequest
from picnic_api.domains.delivery.models import DeliveryDetail
from picnic_api.models.common import PriceDecorator, PromoDecorator, UnknownDecorator
from tests import samples


def test_decorators_parse_by_type_and_keep_unknown_ones() -> None:
    cart = Cart.model_validate(obj=samples.CART)

    decorators = cart.items[0].items[0].decorators

    assert [type(decorator) for decorator in decorators] == [PriceDecorator, PromoDecorator, UnknownDecorator]
    assert decorators[2].raw() == {"type": "SOMETHING_NEW", "value": 1}


def test_unknown_fields_survive_a_round_trip() -> None:
    payload = samples.CART | {"new_field": {"nested": True}}

    assert Cart.model_validate(obj=payload).raw()["new_field"] == {"nested": True}


def test_an_empty_cart_parses_without_analytics_items() -> None:
    payload = samples.CART | {"items": [], "analytics_context_data": {}}

    assert Cart.model_validate(obj=payload).analytics_context_data.items_list == []


def test_aliased_keys_are_read_and_written_as_the_api_sends_them() -> None:
    request = ConsentRequest.model_validate(obj=samples.CONSENT_REQUEST)

    assert request.formatted_content is not None
    assert request.formatted_content.text_html == "<p>Ads</p>"
    assert request.raw()["formatted_content"] == {"text/html": "<p>Ads</p>", "text/plain": "Ads"}


def test_selling_unit_contexts_default_their_type() -> None:
    assert MealPlanContext(day_offset=1, servings=2).model_dump() == {
        "type": "MEAL_PLAN",
        "day_offset": 1,
        "servings": 2,
    }
    assert SellingGroupContext(recipe_id="r", ingredient_id="i", component_type="CORE").type == "SELLING_GROUP"


def test_delivery_detail_holds_full_orders() -> None:
    detail = DeliveryDetail.model_validate(obj=samples.DELIVERY_DETAIL)

    assert detail.orders[0].items[0].items[0].name == "Affligem blond"
    assert detail.returned_containers[0].localized_name == "Krat"
