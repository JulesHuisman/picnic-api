from typing import Any

from picnic_api.models.common import PicnicModel


class BusinessDetails(PicnicModel):
    business_name: str | None = None
    business_registration_number: str | None = None
    sector: str | None = None
    employee_count: int | None = None


class MgmDetails(PicnicModel):
    """Member-get-member referral details."""

    mgm_code: str
    invitee_value: int
    inviter_value: int
    share_url: str
    amount_earned: int


class Address(PicnicModel):
    id: str | None = None
    house_number: int
    house_number_ext: str | None = None
    postcode: str
    street: str
    city: str


class Subscription(PicnicModel):
    list_id: str
    subscribed: bool
    name: str


class HouseholdDetails(PicnicModel):
    adults: int
    children: int
    cats: int
    dogs: int
    author: str
    last_edit_ts: int


class FeatureToggle(PicnicModel):
    name: str


class User(PicnicModel):
    """The logged in user. `consent_decisions` maps consent keys (e.g. `MISC_COMMERCIAL_ADS`) to decisions."""

    user_id: str
    firstname: str
    lastname: str
    address: Address
    phone: str
    contact_email: str
    feature_toggles: list[FeatureToggle]
    push_subscriptions: list[Subscription]
    subscriptions: list[Subscription]
    customer_type: str
    household_details: HouseholdDetails
    business_details: BusinessDetails | None = None
    check_general_consent: bool
    placed_order: bool
    received_delivery: bool
    total_deliveries: int
    completed_deliveries: int
    consent_decisions: dict[str, bool]


class UserInfo(PicnicModel):
    user_id: str
    redacted_phone_number: str
    feature_toggles: list[FeatureToggle]


class UpdateCheckResult(PicnicModel):
    update_required: bool
    address_autocomplete_enabled_countries: list[str]
    use_address_autocomplete_flow: bool


class Avatar(PicnicModel):
    image_url: str
    type: str


class ProfileUser(PicnicModel):
    name: str
    address: Address
    avatar: Avatar
    mgm: MgmDetails


class ProfileMenu(PicnicModel):
    highlights: list[Any]
    user: ProfileUser
