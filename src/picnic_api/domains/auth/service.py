import hashlib
import json

from picnic_api.domains.auth.models import LoginResult, Verify2FAResult
from picnic_api.errors import PicnicError
from picnic_api.http_client import HttpClient, describe_error

CLIENT_ID = 30100
AUTH_HEADER = "x-picnic-auth"


class AuthService:
    """Login, logout, 2FA and phone verification."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def login(self, username: str, password: str) -> LoginResult:
        """Logs the user in and stores the returned auth key on the client for subsequent requests."""
        secret = hashlib.md5(password.encode("utf-8")).hexdigest()
        response = self._http.session.post(
            url=f"{self._http.url}/user/login",
            headers=self._http.base_headers,
            content=json.dumps(obj={"key": username, "secret": secret, "client_id": CLIENT_ID}),
        )
        if response.is_error:
            raise PicnicError(f"Login failed: {describe_error(response=response)}")

        auth_key = response.headers.get(AUTH_HEADER)
        if not auth_key:
            raise PicnicError("Login failed: No auth key received.")

        self._http.auth_key = auth_key
        data = response.json()
        return LoginResult(
            auth_key=auth_key,
            user_id=data.get("user_id"),
            second_factor_authentication_required=data.get("second_factor_authentication_required"),
            show_second_factor_authentication_intro=data.get("show_second_factor_authentication_intro"),
        )

    def generate_2fa_code(self, channel: str) -> None:
        """Sends a 2FA code to the user. `SMS` is the only known channel."""
        self._http.send_request(
            method="POST", path="/user/2fa/generate", data={"channel": channel}, include_picnic_headers=True
        )

    def verify_2fa_code(self, code: str) -> Verify2FAResult:
        """Verifies a 2FA code and stores the new auth key the API returns in the response headers (HTTP 204)."""
        response = self._http.session.post(
            url=f"{self._http.url}/user/2fa/verify",
            headers=self._http.base_headers | self._http.picnic_headers,
            content=json.dumps(obj={"otp": code}),
        )
        if response.is_error:
            raise PicnicError(f"2FA verification failed: {describe_error(response=response)}")

        auth_key = response.headers.get(AUTH_HEADER)
        if not auth_key:
            raise PicnicError("2FA verification failed: No auth key received.")

        self._http.auth_key = auth_key
        return Verify2FAResult(auth_key=auth_key)

    def logout(self) -> None:
        """Logs the current user out, invalidating the auth key."""
        self._http.send_request(method="POST", path="/user/logout")

    def generate_phone_verification_code(self, phone_number: str) -> None:
        """Sends a verification code to the given phone number."""
        self._http.send_request(
            method="POST", path="/user/phone_verification/generate", data={"phone_number": phone_number}
        )

    def verify_phone_number(self, phone_number: str, code: str) -> None:
        """Verifies a phone number with the code sent to it."""
        self._http.send_request(
            method="POST",
            path="/user/phone_verification/verify",
            data={"otp": code, "phone_number": phone_number},
        )
