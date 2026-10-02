import hashlib
import json

import httpx
import pytest

from picnic_api import PicnicClient, PicnicError
from tests.conftest import BASE_URL, MockApi


def test_login_stores_the_auth_key(client: PicnicClient, api: MockApi) -> None:
    api.queue(
        httpx.Response(
            status_code=200,
            headers={"x-picnic-auth": "login-key"},
            json={
                "user_id": "user-1",
                "second_factor_authentication_required": True,
                "show_second_factor_authentication_intro": False,
            },
        )
    )

    result = client.auth.login(username="sam@example.com", password="secret")

    assert result.auth_key == "login-key"
    assert result.user_id == "user-1"
    assert result.second_factor_authentication_required is True
    assert client.auth_key == "login-key"
    assert str(api.last.url) == f"{BASE_URL}/user/login"
    assert json.loads(api.last.content) == {
        "key": "sam@example.com",
        "secret": hashlib.md5(b"secret").hexdigest(),
        "client_id": 30100,
    }


@pytest.mark.parametrize(
    argnames=("response", "message"),
    argvalues=[
        (
            httpx.Response(status_code=401, json={"error": {"message": "Wrong password"}}),
            "Login failed: Wrong password",
        ),
        (httpx.Response(status_code=503, text="down"), "Login failed: 503 Service Unavailable"),
        (httpx.Response(status_code=200, json={}), "Login failed: No auth key received."),
    ],
)
def test_login_failures(client: PicnicClient, api: MockApi, response: httpx.Response, message: str) -> None:
    api.queue(response)

    with pytest.raises(PicnicError, match=message):
        client.auth.login(username="sam@example.com", password="secret")

    assert client.auth_key == "initial-auth-key"


def test_verify_2fa_captures_the_new_auth_key(client: PicnicClient, api: MockApi) -> None:
    api.queue(httpx.Response(status_code=204, headers={"x-picnic-auth": "new-2fa-auth-key"}))

    result = client.auth.verify_2fa_code(code="123456")

    assert result.auth_key == "new-2fa-auth-key"
    assert client.auth_key == "new-2fa-auth-key"


def test_verify_2fa_sends_the_code_with_picnic_headers(client: PicnicClient, api: MockApi) -> None:
    api.queue(httpx.Response(status_code=204, headers={"x-picnic-auth": "new-key"}))

    client.auth.verify_2fa_code(code="654321")

    assert api.last.method == "POST"
    assert str(api.last.url) == f"{BASE_URL}/user/2fa/verify"
    assert json.loads(api.last.content) == {"otp": "654321"}
    assert api.last.headers["x-picnic-auth"] == "initial-auth-key"
    assert api.last.headers["x-picnic-agent"]
    assert api.last.headers["x-picnic-did"]


@pytest.mark.parametrize(
    argnames=("response", "message"),
    argvalues=[
        (httpx.Response(status_code=204), "No auth key received"),
        (httpx.Response(status_code=401, json={"error": {"message": "Invalid OTP"}}), "Invalid OTP"),
        (httpx.Response(status_code=500), "500 Internal Server Error"),
    ],
)
def test_verify_2fa_failures(client: PicnicClient, api: MockApi, response: httpx.Response, message: str) -> None:
    api.queue(response)

    with pytest.raises(PicnicError, match=message):
        client.auth.verify_2fa_code(code="000000")
