from picnic_api.http_client import HttpClient
from picnic_api.models.fusion import PmlDocument


class ContentService:
    """Static content pages."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    async def get_faq_content(self) -> PmlDocument:
        """Returns the FAQ / help section content as PML."""
        return PmlDocument.model_validate(
            obj=await self._http.send_request(method="GET", path="/content/faq", include_picnic_headers=True)
        )

    async def get_search_empty_state(self) -> PmlDocument:
        """Returns the content of the empty search results screen as PML."""
        return PmlDocument.model_validate(
            obj=await self._http.send_request(
                method="GET", path="/content/search_empty_state", include_picnic_headers=True
            )
        )
