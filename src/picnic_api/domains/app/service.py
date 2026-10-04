from typing import Any

from picnic_api.domains.app.models import DeeplinkResolution
from picnic_api.domains.app.rsc import parse_rsc_payload
from picnic_api.errors import UnexpectedPageFormatError
from picnic_api.http_client import HttpClient
from picnic_api.models.fusion import BootstrapData, FusionPage
from picnic_api.models.rsc import RscPage


class AppService:
    """Bootstrap data, pages and deeplink resolution."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    async def get_bootstrap_data(self) -> BootstrapData:
        """Returns the bootstrap data: tab bar configuration, third-party SDK configs and feature flags."""
        return BootstrapData.model_validate(obj=await self._http.send_request(method="GET", path="/bootstrap"))

    async def get_page(self, page_id: str) -> FusionPage:
        """Returns a Fusion page by its page id, optionally followed by `?` and query parameters.

        Known page ids: `home_page_root`, `purchases-page-root`, `meals-page-root`, `slot-selector-root`,
        `parcels-overview-page-root`, `empty-search-page-root`, `search-page-results?search_term=<term>`,
        `product-details-page-root?id=<selling_unit_id>`, `L1-category-page-root?category_id=<id>`,
        `L2-category-page-root?category_id=<id>`, `delivery-receipt-page?delivery_id=<id>` and
        `parcel-tracking-page-root?parcel_id=<id>`.

        Raises `UnexpectedPageFormatError` for pages served as RSC (known: `category-tree-root`, `profile-root`,
        `promo-group-deep-dive?promo_group_id=<id>`); fetch those with `get_rsc_page`.
        """
        page = await self._fetch_page(page_id=page_id)
        if isinstance(page, str):
            raise UnexpectedPageFormatError(page_id=page_id, received_format="rsc")
        return FusionPage.model_validate(obj=page)

    async def get_rsc_page(self, page_id: str) -> RscPage:
        """Returns a page served as a React Server Components payload, split into its rows.

        Raises `UnexpectedPageFormatError` when the page is served as a Fusion page; use `get_page` for those.
        """
        page = await self._fetch_page(page_id=page_id)
        if not isinstance(page, str):
            raise UnexpectedPageFormatError(page_id=page_id, received_format="fusion")
        return parse_rsc_payload(payload=page)

    async def resolve_deeplink(self, url: str) -> DeeplinkResolution:
        """Resolves a Picnic deeplink (e.g. `https://picnic.app/nl/deeplink/...`) to its target."""
        return DeeplinkResolution.model_validate(
            obj=await self._http.send_request(
                method="POST", path="/deeplink/resolve", data={"url": url}, include_picnic_headers=True
            )
        )

    async def _fetch_page(self, page_id: str) -> Any:
        return await self._http.send_request(method="GET", path=f"/pages/{page_id}", include_picnic_headers=True)
