import json
import re
from typing import Any
from urllib.parse import quote

from picnic_api.domains.app.models import DeeplinkResolution
from picnic_api.domains.app.rsc import module_chunks, parse_rsc_payload
from picnic_api.errors import PicnicError, UnexpectedPageFormatError
from picnic_api.http_client import HttpClient
from picnic_api.models.fusion import BootstrapData, FusionPage
from picnic_api.models.rsc import RscPage


class AppService:
    """Bootstrap data, pages and deeplink resolution."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http
        self._action_ids: dict[tuple[str, str], str | None] = {}

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

    async def find_server_action_id(self, page: RscPage, module_path: str, action_name: str) -> str | None:
        """Finds the id of a server action, such as `act_fetchSearchResults_169995c7443462f7`, the way the app does.

        The id sits in the client chunks of the component whose path ends with `module_path` and changes when
        Picnic deploys. Chunk names carry a content hash, so the result per chunk is cached for this client.
        """
        pattern = re.compile(rf"act_{action_name}_[0-9a-f]+")
        for chunk in module_chunks(page=page, module_path=module_path):
            key = (chunk, action_name)
            if key not in self._action_ids:
                match = pattern.search(await self._client_chunk(chunk=chunk))
                self._action_ids[key] = match.group(0) if match else None
            if self._action_ids[key]:
                return self._action_ids[key]
        return None

    async def run_server_action(self, action_id: str, args: list[Any]) -> RscPage:
        """Runs a server action of an RSC page, with the arguments its client component passes, and returns the
        RSC payload it responds with."""
        payload = await self._http.send_request(
            method="POST",
            path=f"/pages/action/{quote(action_id, safe='')}",
            data={"params": json.dumps(args)},
            include_picnic_headers=True,
        )
        return parse_rsc_payload(payload=payload)

    async def _client_chunk(self, chunk: str) -> str:
        """Downloads a client chunk from the CDN in the bootstrap data. Chunks are public, so no auth key is sent."""
        config = (await self.get_bootstrap_data()).in_app_feature_config
        base_url = config.client_component_cdn_base_url if config else None
        if not base_url:
            raise PicnicError("The bootstrap data has no client_component_cdn_base_url")
        response = await self._http.session.get(url=f"{base_url.rstrip('/')}/{chunk}.script.bundle")
        if response.is_error:
            raise PicnicError(f"Client chunk {chunk}: {response.status_code} {response.reason_phrase}")
        return response.text

    async def resolve_deeplink(self, url: str) -> DeeplinkResolution:
        """Resolves a Picnic deeplink (e.g. `https://picnic.app/nl/deeplink/...`) to its target."""
        return DeeplinkResolution.model_validate(
            obj=await self._http.send_request(
                method="POST", path="/deeplink/resolve", data={"url": url}, include_picnic_headers=True
            )
        )

    async def _fetch_page(self, page_id: str) -> Any:
        return await self._http.send_request(method="GET", path=f"/pages/{page_id}", include_picnic_headers=True)
