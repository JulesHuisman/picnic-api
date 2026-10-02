from typing import Literal

from picnic_api.models.common import PicnicModel
from picnic_api.models.fusion import PriceRange


class SearchSuggestion(PicnicModel):
    type: Literal["SEARCH_SUGGESTION"]
    id: str
    suggestion: str


class ProductInfoSection(PicnicModel):
    """A collapsible info section of the product details page (e.g. ingredients, nutritional values)."""

    title: str
    content: str


class ProductPromotion(PicnicModel):
    """Promotion label attached to a product (e.g. "1+1 gratis")."""

    id: str
    label: str


class BundleItem(PicnicModel):
    """A buy-more-pay-less bundle option. `price_per_unit` is in cents."""

    id: str
    quantity: int
    price_per_unit: int
    image_id: str
    max_count: int


class SimilarProduct(PicnicModel):
    """A similar or alternative product shown on the product details page. Prices are in cents."""

    id: str
    name: str
    image_id: str
    display_price: int
    unit_quantity: str
    max_count: int
    deposit: int | None = None
    price_ranges: list[PriceRange] | None = None


class ProductDetails(PicnicModel):
    """Structured product details extracted from the Fusion product details page. Prices are in cents.

    `price_ranges` is usually only found in the page's PML script parameters; search results carry it on
    the `SellingUnit` instead.
    """

    id: str
    name: str
    brand: str | None
    unit_quantity: str
    unit_price: str | None
    display_price: int
    max_count: int
    image_ids: list[str]
    description: str | None
    highlights: list[str]
    allergens: list[str]
    info_sections: list[ProductInfoSection]
    promotion: ProductPromotion | None
    bundles: list[BundleItem]
    price_ranges: list[PriceRange] | None
    similar_products: list[SimilarProduct]
