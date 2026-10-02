from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class PicnicModel(BaseModel):
    """Base model for Picnic data. Unknown fields are kept so API additions never break parsing."""

    model_config = ConfigDict(extra="allow", validate_by_name=True, validate_by_alias=True, serialize_by_alias=True)

    def raw(self) -> dict[str, Any]:
        """Returns the data as the JSON the API sent."""
        return self.model_dump(exclude_unset=True)


class CamelModel(PicnicModel):
    """Base model for payloads whose keys are camelCase."""

    model_config = ConfigDict(alias_generator=to_camel)


type CountryCode = Literal["NL", "DE", "FR"]

type ImageSize = Literal["tiny", "small", "medium", "large", "extra-large"]


class Link(PicnicModel):
    type: str
    href: str


class BasePriceDecorator(PicnicModel):
    type: Literal["BASE_PRICE"]
    base_price_text: str


class FreshLabelDecorator(PicnicModel):
    type: Literal["FRESH_LABEL"]
    period: str


class LabelDecorator(PicnicModel):
    type: Literal["LABEL"]
    text: str


class PriceDecorator(PicnicModel):
    type: Literal["PRICE"]
    display_price: int


class QuantityDecorator(PicnicModel):
    type: Literal["QUANTITY"]
    quantity: int


class BackgroundImageDecorator(PicnicModel):
    type: Literal["BACKGROUND_IMAGE"]
    image_ids: list[str]
    height_percent: float


class DeeplinkReference(PicnicModel):
    type: Literal["DEEPLINK"]
    target: str


class SubBanner(PicnicModel):
    banner_id: str
    image_id: str
    display_time: str
    description: str
    reference: DeeplinkReference
    position: str


class BannersDecorator(PicnicModel):
    type: Literal["BANNERS"]
    height_percentage: float
    banners: list[SubBanner]


class UnitQuantityDecorator(PicnicModel):
    type: Literal["UNIT_QUANTITY"]
    unit_quantity_text: str


class OrderedQuantityDecorator(PicnicModel):
    type: Literal["ORDERED_QUANTITY"]
    image_id: str
    quantity: str


class ProductSizeDecorator(PicnicModel):
    type: Literal["PRODUCT_SIZE"]
    text: str


class ValidityLabelDecorator(PicnicModel):
    type: Literal["VALIDITY_LABEL"]
    valid_until: str


class Position(PicnicModel):
    start_index: int
    length: int


class Style(PicnicModel):
    position: Position
    color: str
    style: str


class TitleStyleDecorator(PicnicModel):
    type: Literal["TITLE_STYLE"]
    styles: list[Style]


class MoreButtonDecorator(PicnicModel):
    type: Literal["MORE_BUTTON"]
    link: Link
    images: list[str]
    sellable_item_count: int


class Explanation(PicnicModel):
    short_explanation: str
    long_explanation: str


type Decorator = Annotated[
    BasePriceDecorator
    | FreshLabelDecorator
    | LabelDecorator
    | PriceDecorator
    | BackgroundImageDecorator
    | BannersDecorator
    | QuantityDecorator
    | UnitQuantityDecorator
    | ValidityLabelDecorator
    | TitleStyleDecorator
    | MoreButtonDecorator
    | UnavailableDecorator
    | ImmutableDecorator
    | ArticleDeliveryFailureDecorator
    | BundlesButtonDecorator
    | PromoDecorator
    | OrderedQuantityDecorator
    | ProductSizeDecorator
    | ProductCharacteristicsDecorator
    | UnknownDecorator,
    Field(union_mode="left_to_right"),
]


class Replacement(PicnicModel):
    type: Literal["REPLACEMENT"]
    display_price: int
    image_id: str
    replacement_type: str
    id: str
    name: str
    unit_quantity: str
    unit_quantity_sub: str | None = None
    price: int
    tags: list[Any]
    decorators: list[Decorator]
    max_count: int


class UnavailableDecorator(PicnicModel):
    type: Literal["UNAVAILABLE"]
    reason: str
    replacements: list[Replacement] | None = None
    deeplink: str
    explanation: Explanation


class Characteristics(PicnicModel):
    baby_month: str | None
    rating: str | None
    score: str | None
    type: Literal["FROZEN"]


class ProductCharacteristicsDecorator(PicnicModel):
    type: Literal["PRODUCT_CHARACTERISTICS"]
    characteristics: list[Characteristics]


type FailureReason = Literal["PRODUCT_ABSENT", "PRODUCT_LOW_QUALITY", "PRODUCT_NOT_SHIPPED"]


class ArticleDeliveryFailureDecorator(PicnicModel):
    type: Literal["ARTICLE_DELIVERY_FAILURES"]
    failures: dict[str, list[FailureReason]]
    prices: dict[str, int]


class ImmutableDecorator(PicnicModel):
    type: Literal["IMMUTABLE"]


class BundlesButtonDecorator(PicnicModel):
    type: Literal["BUNDLES_BUTTON"]
    icon_color: str
    deeplink: str
    background_color: str


class PromoDecorator(PicnicModel):
    """Promotional label decorator (e.g. "BundelBonus"), seen on order lines with bundle discounts."""

    type: Literal["PROMO"]
    text: str
    background_color: str
    text_color: str


class UnknownDecorator(PicnicModel):
    """Any decorator type this client does not model yet."""

    type: str
