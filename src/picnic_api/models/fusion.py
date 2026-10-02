"""Models for Fusion/PML pages and the bootstrap response.

PML component trees are open-ended and evolve with every app release, so they are kept as raw JSON
(`dict[str, Any]`). Only the stable envelopes around them are modelled.
"""

from typing import Any

from pydantic import Field, model_validator

from picnic_api.models.common import PicnicModel


class TrackingAttributes(PicnicModel):
    template_variant_id: str
    entity_ids: list[str]


class PmlDocument(PicnicModel):
    """A PML document: a component tree plus the images it references."""

    pml_version: str
    component: dict[str, Any]
    images: dict[str, str] | None = None
    tracking_attributes: TrackingAttributes | None = None


class PriceRange(PicnicModel):
    """A single tier in a progressive (bundle) discount schedule."""

    price: int
    from_quantity: int


class SellingUnit(PicnicModel):
    """A product as embedded in Fusion pages. Pages often carry partial selling units, so only `id` is required."""

    id: str
    name: str | None = None
    image_id: str | None = None
    display_price: int | None = None
    unit_quantity: str | None = None
    max_count: int | None = None
    decorators: list[Any] | None = None
    price_ranges: list[PriceRange] | None = None


class CartValueDynamicIconConfig(PicnicModel):
    type: str
    lower_bound: float | None = None
    upper_bound: float | None = None


class TabIcon(PicnicModel):
    """A tab bar icon. `type` is `PRESET`, `BASE_64` or `UNSUPPORTED`."""

    type: str
    preset: str | None = None
    value: str | None = None
    dynamic_config: CartValueDynamicIconConfig | None = None
    allow_tint_color: bool | None = None


class IconConfig(PicnicModel):
    icons: list[TabIcon]
    highlight_icons: list[TabIcon] | None = None
    color: str
    highlight_color: str


class TabTarget(PicnicModel):
    """Navigation target of a tab. `type` is `PICNIC_PAGE_REFERENCE`, `DEEPLINK` or `UNSUPPORTED`."""

    type: str
    reference: str | None = None
    request_params: dict[str, str] | None = None
    deeplink: str | None = None


class TabDecorator(PicnicModel):
    type: str
    display_positions_to_notify: list[str] | None = None


class TabAccessibility(PicnicModel):
    label: str
    hint: str


class MessageBehaviour(PicnicModel):
    display_positions_to_render: list[str]


class GeneralMessageBehaviour(PicnicModel):
    display_positions_to_poll: list[str]


class TitleConfig(PicnicModel):
    title: str
    color: str
    highlight_color: str


class BootstrapTab(PicnicModel):
    id: str
    tab_type: str
    analytics_id: str | None = None
    icon_config: IconConfig
    message_behaviour: MessageBehaviour
    tab_decorators: list[TabDecorator] | None = None
    accessibility: TabAccessibility
    target: TabTarget | None = None
    header: str | None = None
    title: str | None = None
    title_config: TitleConfig | None = None


class BrazeConfig(PicnicModel):
    authentication_token: str


class DatadogConfig(PicnicModel):
    rum_session_sample_rate: float
    apm_trace_sample_rate: float


class CartPreCheckoutUpsellConfig(PicnicModel):
    timeout_ms: int | None


class InAppFeatureConfig(PicnicModel):
    cart_pre_checkout_upsell_check: CartPreCheckoutUpsellConfig | None = None


class BootstrapData(PicnicModel):
    """The response of `GET /bootstrap`: tab bar configuration, third-party SDK configs and feature flags."""

    landing_tab_id: str
    tabs: list[BootstrapTab]
    general_message_behaviour: GeneralMessageBehaviour
    datadog_config: DatadogConfig | None
    braze_config: BrazeConfig | None
    in_app_feature_config: InAppFeatureConfig | None
    first_time_user: bool


class PageAnalytics(PicnicModel):
    type: str | None = None
    contexts: list[dict[str, Any]] | None = None
    domain: str | None = None
    name: str | None = None
    version: str | None = None


class PageHeader(PicnicModel):
    """Page header. `type` is `STATIC`, `DEFAULT` or another header kind."""

    type: str
    title: str | None = None
    buttons: list[Any] | None = None


class FusionPageLayout(PicnicModel):
    """The layout of a page: its id, presentation, header and component tree (`body`, raw JSON)."""

    id: str | None = None
    analytics: PageAnalytics | None = None
    presentation: dict[str, Any] | None = None
    header: PageHeader | None = None
    body: dict[str, Any]


class FusionPage(PicnicModel):
    """Page response of `GET /pages/{page_id}`: the layout plus PML script expressions keyed by name."""

    script: dict[str, Any] = Field(default_factory=dict)
    layout: FusionPageLayout

    @model_validator(mode="before")
    @classmethod
    def wrap_bare_layout(cls, data: Any) -> Any:
        """Wraps pages served as a bare layout (e.g. `home_page_root`) in the `{script, layout}` envelope."""
        return {"layout": data} if isinstance(data, dict) and "layout" not in data and "body" in data else data
