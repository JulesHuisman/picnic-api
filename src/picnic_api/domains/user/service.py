from typing import Any

from picnic_api.domains.user.models import ProfileMenu, UpdateCheckResult, User, UserInfo
from picnic_api.http_client import HttpClient


class UserService:
    """User details, profile, suggestions and push tokens."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    async def get_user_details(self) -> User:
        """Returns the details of the logged in user."""
        return User.model_validate(obj=await self._http.send_request(method="GET", path="/user"))

    async def get_user_info(self) -> UserInfo:
        """Returns information about the user such as toggled features."""
        return UserInfo.model_validate(obj=await self._http.send_request(method="GET", path="/user-info"))

    async def get_profile_menu(self) -> ProfileMenu:
        """Returns the profile section, including member-get-member referral details in `user.mgm`."""
        return ProfileMenu.model_validate(
            obj=await self._http.send_request(
                method="GET", path="/profile-menu?fetch_mgm=true", include_picnic_headers=True
            )
        )

    async def submit_suggestion(self, suggestion: str) -> Any:
        """Submits a suggestion or feedback. Untested route; the response shape is unknown."""
        return await self._http.send_request(method="POST", path="/user/suggestion", data={"suggestion": suggestion})

    async def register_push_token(self, push_token: str, platform: str) -> Any:
        """Registers a push notification token (e.g. platform `firebase`). Untested route; the response is unknown."""
        return await self._http.send_request(
            method="POST", path="/user/device/register_push", data={"push_token": push_token, "platform": platform}
        )

    async def check_for_updates(self) -> UpdateCheckResult:
        """Checks whether a newer app version is available, describing the client from its `device_id` and `agent`."""
        agent_parts = self._http.agent.split(";")
        version_parts = (agent_parts[1] if len(agent_parts) > 1 else "").split("-")
        body = {
            "device_id": self._http.device_id,
            "device_name": "notAvailable",
            "client_id": agent_parts[0],
            "version": version_parts[0],
            "device_os": self._http.agent,
            "build_number": version_parts[1] if len(version_parts) > 1 else "",
        }
        return UpdateCheckResult.model_validate(
            obj=await self._http.send_request(
                method="POST", path="/update_check", data=body, include_picnic_headers=True
            )
        )
