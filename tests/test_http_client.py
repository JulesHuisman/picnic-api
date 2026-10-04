import httpx
import pytest

from picnic_api import CheckoutIssueError, PicnicAuthError, PicnicClient, PicnicError
from picnic_api.http_client import HttpClient
from tests.conftest import BASE_URL, MockApi


@pytest.mark.parametrize(
    argnames=("country_code", "url", "language"),
    argvalues=[
        ("NL", "https://storefront-prod.nl.picnicinternational.com/api/15", "nl"),
        ("DE", "https://storefront-prod.de.picnicinternational.com/api/15", "de"),
        ("FR", "https://storefront-prod.fr.picnicinternational.com/api/15", "fr"),
    ],
)
def test_defaults_follow_the_country(country_code: str, url: str, language: str) -> None:
    http = HttpClient(country_code=country_code)

    assert http.url == url
    assert http.base_headers["Accept-Language"] == language
    assert "x-picnic-auth" not in http.base_headers
    assert http.picnic_headers == {"x-picnic-agent": "30100;1.246.1-15599;", "x-picnic-did": "3C417201548B2E3B"}


def test_custom_options() -> None:
    http = HttpClient(api_version="16", url="https://example.com/api", device_id="did", agent="agent", auth_key="key")

    assert http.url == "https://example.com/api"
    assert http.base_headers["x-picnic-auth"] == "key"
    assert http.picnic_headers == {"x-picnic-agent": "agent", "x-picnic-did": "did"}


async def test_api_version_is_part_of_the_default_url() -> None:
    assert HttpClient(api_version="16").url.endswith("/api/16")


async def test_sends_json_with_base_headers(client: PicnicClient, api: MockApi) -> None:
    api.queue_json({"ok": True})

    result = await client.send_request(method="POST", path="/invite/friend", data={"email": "friend@example.com"})

    assert result == {"ok": True}
    assert str(api.last.url) == f"{BASE_URL}/invite/friend"
    assert api.last.content == b'{"email":"friend@example.com"}'
    assert api.last.headers["Content-Type"] == "application/json; charset=UTF-8"
    assert api.last.headers["User-Agent"] == "okhttp/4.9.0"


async def test_absolute_urls_are_used_as_is(client: PicnicClient, api: MockApi) -> None:
    await client.send_request(method="GET", path="https://example.com/elsewhere")

    assert str(api.last.url) == "https://example.com/elsewhere"


async def test_bytes_are_sent_raw_with_their_content_type(client: PicnicClient, api: MockApi) -> None:
    await client.send_request(method="POST", path="/upload", data=b"\x01\x02", content_type="image/png")
    assert api.last.content == b"\x01\x02"
    assert api.last.headers["Content-Type"] == "image/png"

    await client.send_request(method="POST", path="/upload", data=bytearray(b"\x03"))
    assert api.last.headers["Content-Type"] == "application/octet-stream"


async def test_image_requests_return_bytes(client: PicnicClient, api: MockApi) -> None:
    api.queue(httpx.Response(status_code=200, content=b"\x89PNG"))

    assert await client.send_request(method="GET", path="/image", is_image_request=True) == b"\x89PNG"


async def test_rsc_payloads_return_text(client: PicnicClient, api: MockApi) -> None:
    api.queue(httpx.Response(status_code=200, text='0:{"a":1}', headers={"content-type": "text/x-component"}))

    assert await client.send_request(method="GET", path="/pages/x") == '0:{"a":1}'


async def test_empty_bodies_return_none(client: PicnicClient, api: MockApi) -> None:
    api.queue(httpx.Response(status_code=204))

    assert await client.send_request(method="POST", path="/user/logout") is None


@pytest.mark.parametrize(
    argnames=("response", "message"),
    argvalues=[
        (httpx.Response(status_code=400, json={"error": {"message": "Invalid slot"}}), "Invalid slot"),
        (httpx.Response(status_code=400, json={"error": {"code": "X"}}), "Bad Request"),
        (httpx.Response(status_code=400, json=["unexpected"]), "Bad Request"),
        (httpx.Response(status_code=500, text="oops"), "500 Internal Server Error - oops"),
        (httpx.Response(status_code=500), "500 Internal Server Error"),
    ],
)
async def test_errors_carry_the_api_message(
    client: PicnicClient, api: MockApi, response: httpx.Response, message: str
) -> None:
    api.queue(response)

    with pytest.raises(PicnicError) as error:
        await client.send_request(method="GET", path="/cart")

    assert str(error.value) == message


async def test_unauthorized_responses_raise_an_auth_error(client: PicnicClient, api: MockApi) -> None:
    api.queue(httpx.Response(status_code=401, json={"error": {"message": "Auth key expired"}}))

    with pytest.raises(PicnicAuthError, match="Auth key expired"):
        await client.send_request(method="GET", path="/cart")


async def test_cart_issues_raise_a_checkout_issue_error(client: PicnicClient, api: MockApi) -> None:
    api.queue(
        httpx.Response(
            status_code=400,
            json={
                "code": "CART_HAS_ISSUES",
                "details": {
                    "type": "LEGACY_ALCOHOL_AGE_VERIFICATION_REQUIRED",
                    "localized_title": "18+",
                    "localized_message": "Confirm age",
                    "resolve_key": "age_verified",
                    "blocking": False,
                },
            },
        )
    )

    with pytest.raises(CheckoutIssueError) as error:
        await client.cart.start_checkout(mts=1)

    assert error.value.resolve_key == "age_verified"
    assert error.value.is_age_verification_issue()


async def test_context_manager_closes_the_session() -> None:
    session = httpx.AsyncClient()

    async with PicnicClient(session=session):
        assert not session.is_closed

    assert session.is_closed
