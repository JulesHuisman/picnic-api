"""Minimal but complete API payloads, shaped like real Picnic responses."""

from typing import Any

PML = {"pml_version": "0.1", "component": {"type": "RICH_TEXT", "markdown": "Hi"}, "images": {}}

DELIVERY_SLOT = {
    "slot_id": "slot-1",
    "hub_id": "hub",
    "fc_id": "fc",
    "window_start": "2026-10-03T17:00:00.000+02:00",
    "window_end": "2026-10-03T18:00:00.000+02:00",
    "cut_off_time": "2026-10-02T22:00:00.000+02:00",
    "is_available": True,
    "selected": True,
    "reserved": False,
    "minimum_order_value": 3500,
    "slot_characteristics": [],
}

ORDER_ARTICLE = {
    "type": "ORDER_ARTICLE",
    "id": "s1001524",
    "name": "Affligem blond",
    "unit_quantity": "6 x 300 ml",
    "price": 865,
    "price_ranges": [{"price": 800, "from_quantity": 2}],
    "decorators": [
        {"type": "PRICE", "display_price": 799},
        {"type": "PROMO", "text": "BundelBonus", "background_color": "#fff", "text_color": "#000"},
        {"type": "SOMETHING_NEW", "value": 1},
    ],
    "max_count": 50,
    "image_ids": ["img"],
    "perishable": False,
    "analytics_contexts": [],
    "selling_unit_contexts_for_mutations": [],
}

ORDER_LINE = {
    "type": "ORDER_LINE",
    "id": "line-1",
    "items": [ORDER_ARTICLE],
    "display_price": 865,
    "price": 865,
}

CART = {
    "type": "ORDER",
    "id": "cart-1",
    "items": [ORDER_LINE],
    "delivery_slots": [DELIVERY_SLOT],
    "selected_slot": {"slot_id": "slot-1", "state": "EXPLICIT"},
    "slot_selector_message": None,
    "total_count": 1,
    "total_price": 865,
    "checkout_total_price": 865,
    "mts": 1234567890,
    "deposit_breakdown": [{"type": "BAG", "value": 25, "count": 1}],
    "decorator_overrides": {},
    "state_token": "jwt",
    "fees": [],
    "basket_sections": [],
    "analytics_context_data": {
        "items_list": [{"product_id": "s1001524", "quantity": 1, "is_available": True, "is_in_recipe": False}]
    },
    "show_create_sellable_banner": False,
    "membership_savings": 0,
}

ORDER = {
    "type": "ORDER",
    "id": "order-1",
    "items": [ORDER_LINE],
    "total_price": 865,
    "checkout_total_price": 865,
    "total_savings": 0,
    "total_deposit": 25,
    "cancellable": False,
    "creation_time": "2026-10-01T10:00:00.000+02:00",
    "status": "COMPLETED",
    "decorator_overrides": {},
    "cancellation_time": None,
}

DELIVERY_TIME = {"start": "2026-10-03T17:00:00.000+02:00", "end": "2026-10-03T18:00:00.000+02:00"}

DELIVERY = {
    "delivery_id": "delivery-1",
    "creation_time": "2026-10-01T10:00:00.000+02:00",
    "slot": DELIVERY_SLOT,
    "eta2": DELIVERY_TIME,
    "status": "COMPLETED",
    "delivery_time": DELIVERY_TIME,
    "orders": [
        {
            "type": "ORDER",
            "id": "order-1",
            "creation_time": "2026-10-01T10:00:00.000+02:00",
            "total_price": 865,
            "status": "COMPLETED",
            "cancellation_time": None,
        }
    ],
}

DELIVERY_DETAIL = DELIVERY | {
    "type": "DELIVERY",
    "id": "delivery-1",
    "orders": [ORDER],
    "returned_containers": [{"type": "CRATE", "localized_name": "Krat", "quantity": 1, "price": 0}],
    "parcels": [],
}

FUSION_PAGE: dict[str, Any] = {
    "script": {},
    "layout": {
        "id": "home_page_root",
        "presentation": {"type": "FULL_SCREEN", "style": {"backgroundColor": "#fff"}},
        "header": None,
        "body": {"type": "STATE_BOUNDARY", "id": "root", "state": {}, "child": {}},
    },
}

BOOTSTRAP = {
    "landing_tab_id": "home",
    "tabs": [
        {
            "id": "home",
            "tab_type": "PAGE",
            "icon_config": {
                "icons": [{"type": "PRESET", "preset": "STOREFRONT"}],
                "color": "#000",
                "highlight_color": "#f00",
            },
            "message_behaviour": {"display_positions_to_render": []},
            "accessibility": {"label": "Home", "hint": "Opens home"},
            "target": {"type": "PICNIC_PAGE_REFERENCE", "reference": "home_page_root"},
        }
    ],
    "general_message_behaviour": {"display_positions_to_poll": ["PROMPT"]},
    "datadog_config": {"rum_session_sample_rate": 0.5, "apm_trace_sample_rate": 0.1},
    "braze_config": None,
    "in_app_feature_config": None,
    "first_time_user": False,
}

CONSENT_SETTING = {
    "type": "CONSENT_SETTING",
    "id": "consent-1",
    "text_id": "text-1",
    "text_locale": "nl",
    "text": {"title": "Ads", "text": "Allow ads", "timestamp": "2026-01-01"},
    "established_decision": True,
    "initial_state": False,
}

CONSENT_REQUEST = {
    "type": "CONSENT_REQUEST",
    "id": "consent-1",
    "text_id": "text-1",
    "text_locale": "nl",
    "formatted_content": {"text/html": "<p>Ads</p>", "text/plain": "Ads"},
}

CONTACT_INFO = {
    "contact_details": {"email": "help@picnic.app", "phone": "+31", "whatsapp": "+31"},
    "opening_times": {"2026-10-02": {"start": [8, 0], "end": [23, 0]}},
}

MESSAGES = {
    "messages": [
        {
            "display_position": "PROMPT",
            "send_correlation_id": "corr",
            "sent_time": 1,
            "expiry_time": 2,
            "user_id": "user",
            "target_entity_id": None,
            "content": PML,
        }
    ],
    "query_interval": 60000,
}

PARCEL = {
    "id": "TRACK1",
    "handler_name": "DHL",
    "active": True,
    "current_status": {"status": "HANDED_OVER", "timestamp": "2026-10-01T10:00:00Z"},
}

DELIVERY_POSITION = {
    "version": 1,
    "scenario_ts": 1,
    "eta": 2,
    "eta_window": DELIVERY_TIME,
    "query_interval": 30000,
    "scenario_in_progress": True,
}

DELIVERY_SCENARIO = {
    "version": 1,
    "scenario": [{"ts": 1, "lat": 52.37, "lng": 4.89}],
    "vehicle": {"image": "base64"},
    "driver": {"name": "Sam"},
}

PAYMENT_PROFILE = {
    "available_payment_method_item": None,
    "available_payment_methods": [{"payment_method": "IDEAL", "available_banks": [{"bank_id": "INGB", "name": "ING"}]}],
    "checkout_banner": None,
    "payment_methods": [
        {
            "brands": [{"brand": "ideal", "display_name": "iDEAL", "icon_url": "url"}],
            "data": {},
            "display_name": "iDEAL",
            "icon_url": "url",
            "payment_method": "IDEAL",
            "visibility": "VISIBLE",
            "visibility_reason": None,
        }
    ],
    "preferred_payment_option_id": "option-1",
    "stored_payment_options": [
        {
            "account": None,
            "brand": "ideal",
            "display_name": "iDEAL",
            "icon_url": "url",
            "id": "option-1",
            "payment_method": "IDEAL",
        }
    ],
}

WALLET_TRANSACTION = {
    "account": "NL**",
    "amount_in_cents": 865,
    "brand": "ideal",
    "display_name": "iDEAL",
    "domains": ["GROCERIES"],
    "icon_url": "url",
    "id": "tx-1",
    "status": "SUCCESS",
    "timestamp": 1,
    "transaction_method": "IDEAL",
    "transaction_type": "PAYMENT",
}

WALLET_TRANSACTION_DETAILS = {
    "amount_in_cents": 865,
    "article_issue_refunds": [],
    "debt_resolution": None,
    "delivery_debt": None,
    "delivery_id": "delivery-1",
    "deposits": [{"count": 1, "type": "BAG", "value": 25}],
    "fees": [],
    "payment_execution_timestamp": 1,
    "payment_method_icon_url": "url",
    "payment_option_account": "NL**",
    "payment_option_display_name": "iDEAL",
    "refunded_items": [],
    "returned_containers": [{"localized_name": "Krat", "price": 0, "quantity": 1, "type": "CRATE"}],
    "shop_items": [ORDER_LINE],
    "transaction_method": "IDEAL",
    "transaction_status": "SUCCESS",
    "transaction_type": "PAYMENT",
}

ADDRESS = {"house_number": 1, "postcode": "1000AA", "street": "Dam", "city": "Amsterdam"}

USER = {
    "user_id": "user-1",
    "firstname": "Sam",
    "lastname": "Jansen",
    "address": ADDRESS,
    "phone": "+31",
    "contact_email": "sam@example.com",
    "feature_toggles": [{"name": "feature"}],
    "push_subscriptions": [{"list_id": "push", "subscribed": True, "name": "Push"}],
    "subscriptions": [],
    "customer_type": "CONSUMER",
    "household_details": {"adults": 2, "children": 0, "cats": 1, "dogs": 0, "author": "user", "last_edit_ts": 1},
    "check_general_consent": False,
    "placed_order": True,
    "received_delivery": True,
    "total_deliveries": 3,
    "completed_deliveries": 3,
    "consent_decisions": {"MISC_COMMERCIAL_ADS": False},
}

USER_INFO = {"user_id": "user-1", "redacted_phone_number": "+31 6 ****", "feature_toggles": []}

PROFILE_MENU = {
    "highlights": [],
    "user": {
        "name": "Sam",
        "address": ADDRESS,
        "avatar": {"image_url": "url", "type": "DEFAULT"},
        "mgm": {
            "mgm_code": "CODE",
            "invitee_value": 1000,
            "inviter_value": 1000,
            "share_url": "url",
            "amount_earned": 0,
        },
    },
}

UPDATE_CHECK = {
    "update_required": False,
    "address_autocomplete_enabled_countries": ["NL"],
    "use_address_autocomplete_flow": True,
}

SELLING_GROUP_CART = {
    "checkoutTotalPrice": 1200,
    "generatedAt": 1,
    "sellingUnits": {
        "s1": {
            "availabilityStatus": {"type": "AVAILABLE"},
            "quantity": 1,
            "contexts": [
                {
                    "quantity": 1,
                    "details": [
                        {
                            "type": "SELLING_GROUP",
                            "sellingGroupId": "recipe",
                            "sellingGroupComponentId": "ingredient",
                            "sellingGroupComponentType": "CORE",
                            "sellingGroupComponentSwapType": None,
                        },
                        {"type": "MEAL_PLAN", "dayRelativeToSlot": 0, "numberOfServings": 2},
                        {"type": "OTHER"},
                    ],
                }
            ],
        }
    },
    "sellingUnitsTotalPrice": 1200,
}
