import json
import re
from typing import Any, Literal, Self

import httpx

from picnic_api.errors import error_class, parse_checkout_issue_error
from picnic_api.models.common import CountryCode

type HttpMethod = Literal["GET", "POST", "PUT", "DELETE"]

DEFAULT_API_VERSION = "15"
DEFAULT_DEVICE_ID = "3C417201548B2E3B"
DEFAULT_AGENT = "30100;1.246.1-15599;"
DEFAULT_TIMEOUT_SECONDS = 30.0
ACCEPT_LANGUAGES: dict[str, str] = {"DE": "de", "FR": "fr"}
ABSOLUTE_URL = re.compile(r"^https?://")


def describe_error(response: httpx.Response) -> str:
    """Returns the API error message of a failed response, falling back to its status line."""
    try:
        data = response.json()
    except ValueError:
        return f"{response.status_code} {response.reason_phrase}"
    error = data.get("error") if isinstance(data, dict) else None
    message = error.get("message") if isinstance(error, dict) else None
    return message or response.reason_phrase


class HttpClient:
    """Async base HTTP client that handles request construction, authentication headers and errors."""

    def __init__(
        self,
        *,
        country_code: CountryCode = "NL",
        api_version: str = DEFAULT_API_VERSION,
        auth_key: str | None = None,
        url: str | None = None,
        device_id: str = DEFAULT_DEVICE_ID,
        agent: str = DEFAULT_AGENT,
        session: httpx.AsyncClient | None = None,
    ) -> None:
        self.country_code = country_code
        self.api_version = api_version
        self.auth_key = auth_key
        self.url = url or f"https://storefront-prod.{country_code.lower()}.picnicinternational.com/api/{api_version}"
        self.device_id = device_id
        self.agent = agent
        self.session = session or httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Closes the underlying HTTP session."""
        await self.session.aclose()

    @property
    def base_headers(self) -> dict[str, str]:
        """Headers sent with every request, including the auth key once known."""
        headers = {
            "User-Agent": "okhttp/4.9.0",
            "Content-Type": "application/json; charset=UTF-8",
            "Accept-Language": ACCEPT_LANGUAGES.get(self.country_code, "nl"),
        }
        if self.auth_key:
            headers["x-picnic-auth"] = self.auth_key
        return headers

    @property
    def picnic_headers(self) -> dict[str, str]:
        """The app identification headers some routes require."""
        return {"x-picnic-agent": self.agent, "x-picnic-did": self.device_id}

    async def send_request(
        self,
        method: HttpMethod,
        path: str,
        data: Any = None,
        include_picnic_headers: bool = False,
        is_image_request: bool = False,
        content_type: str | None = None,
    ) -> Any:
        """Sends a request to the API. Can be used for routes not covered by the domain services.

        `data` is sent as JSON, except `bytes`, which are sent as-is with `content_type` (default
        `application/octet-stream`). `path` is appended to the API url unless it is an absolute URL.

        Returns the parsed JSON body, the raw bytes when `is_image_request` is set, the text of a React Server
        Components payload (`text/x-component`), or None for an empty body. Raises `CheckoutIssueError` for cart
        issues, `PicnicAuthError` for HTTP 401 and `PicnicError` for any other failed response.
        """
        is_raw_body = isinstance(data, (bytes, bytearray, memoryview))
        headers = self.base_headers | (self.picnic_headers if include_picnic_headers else {})
        if is_raw_body:
            headers["Content-Type"] = content_type or "application/octet-stream"
            content = bytes(data)
        else:
            content = None if data is None else json.dumps(obj=data, separators=(",", ":")).encode()

        request_url = path if ABSOLUTE_URL.match(path) else f"{self.url}{path}"
        response = await self.session.request(method=method, url=request_url, headers=headers, content=content)

        if response.is_error:
            self._raise_for_error(response=response)
        if is_image_request:
            return response.content
        if "text/x-component" in response.headers.get("content-type", ""):
            return response.text
        if not response.content:
            return None
        return response.json()

    @staticmethod
    def _raise_for_error(response: httpx.Response) -> None:
        try:
            error_data = response.json()
        except ValueError:
            body = f" - {response.text}" if response.text else ""
            raise error_class(status_code=response.status_code)(
                f"{response.status_code} {response.reason_phrase}{body}"
            ) from None
        if checkout_issue := parse_checkout_issue_error(body=error_data):
            raise checkout_issue
        raise error_class(status_code=response.status_code)(describe_error(response=response))
