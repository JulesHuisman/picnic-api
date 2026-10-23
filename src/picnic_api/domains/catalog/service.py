import base64
from urllib.parse import quote

from pydantic import TypeAdapter

from picnic_api.domains.app.rsc import find_element_props
from picnic_api.domains.app.service import AppService
from picnic_api.domains.catalog.helpers import extract_product_details, extract_search_results
from picnic_api.domains.catalog.models import ProductDetails, SearchSuggestion
from picnic_api.errors import PicnicError
from picnic_api.http_client import HttpClient
from picnic_api.models.common import ImageSize
from picnic_api.models.fusion import FusionPage, SellingUnit

SEARCH_SUGGESTIONS = TypeAdapter(list[SearchSuggestion])
SEARCH_PARAMS_MODULE = "search-page-params/search-page-params-provider.tsx"
SEARCH_RESULTS_MODULE = "search-page-content/results/index.tsx"


class CatalogService:
    """Product search, suggestions, details and images."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http
        self._app = AppService(http=http)

    async def search(self, query: str) -> list[SellingUnit]:
        """Searches for products matching the query, in the order the app shows them.

        Like the app, this fetches the search page for its search ids, then runs the page's `fetchSearchResults`
        server action, which returns the results. Raises `PicnicError` when the page or the results change shape.
        """
        page = await self._app.get_rsc_page(page_id=f"search-page-results?search_term={quote(query, safe='')}")
        params = next(
            (props["params"] for props in find_element_props(page=page, module_path=SEARCH_PARAMS_MODULE)), None
        )
        action_id = await self._app.find_server_action_id(
            page=page, module_path=SEARCH_RESULTS_MODULE, action_name="fetchSearchResults"
        )
        if params is None or action_id is None:
            raise PicnicError("The search page has no search parameters or fetchSearchResults action")
        results = await self._app.run_server_action(
            action_id=action_id,
            args=[
                {
                    "requestedSorting": "RELEVANCE",
                    "searchId": params["searchId"],
                    "searchQuery": query,
                    "searchSessionId": params["searchSessionId"],
                }
            ],
        )
        root = results.rows.get("0")
        if not (isinstance(root, list) and len(root) == 4 and root[0] == "$"):
            raise PicnicError("Unexpected fetchSearchResults response")
        return extract_search_results(results=root[3])

    async def get_suggestions(self, query: str) -> list[SearchSuggestion]:
        """Returns search suggestions for the query."""
        return SEARCH_SUGGESTIONS.validate_python(
            await self._http.send_request(method="GET", path=f"/suggest?search_term={quote(query, safe='')}")
        )

    async def get_product_details_page(self, product_id: str) -> FusionPage:
        """Returns the raw product details page."""
        return FusionPage.model_validate(
            obj=await self._http.send_request(
                method="GET",
                path=(
                    f"/pages/product-details-page-root?id={product_id}"
                    "&show_category_action=true&show_remove_from_purchases_page_action=true"
                ),
                include_picnic_headers=True,
            )
        )

    async def get_product_details(self, product_id: str) -> ProductDetails:
        """Returns structured product details parsed from the product details page.

        Experimental: this parses dynamic Fusion page structures and may break when Picnic changes its layout.
        Use `get_product_details_page` for the raw page.
        """
        return extract_product_details(
            product_id=product_id, page=await self.get_product_details_page(product_id=product_id)
        )

    async def get_image(self, image_id: str, size: ImageSize) -> bytes:
        """Returns a product image as PNG bytes."""
        static_url = self._http.url.split("/api/")[0]
        return await self._http.send_request(
            method="GET", path=f"{static_url}/static/images/{image_id}/{size}.png", is_image_request=True
        )

    async def get_image_as_data_uri(self, image_id: str, size: ImageSize) -> str:
        """Returns a product image as a PNG data URI."""
        image = await self.get_image(image_id=image_id, size=size)
        return f"data:image/png;base64,{base64.b64encode(image).decode()}"
