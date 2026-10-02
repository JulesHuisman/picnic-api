from typing import Any

from picnic_api.http_client import HttpClient


class UserOnboardingService:
    """Household and business details and push subscriptions during onboarding. These routes are untested."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def set_household_details(self, details: dict[str, Any]) -> Any:
        """Submits household details used to personalise the shop. The exact shape is unknown."""
        return self._http.send_request(method="POST", path="/user-onboarding/household-details", data=details)

    def set_business_details(self, details: dict[str, Any]) -> Any:
        """Submits business details for business accounts. The exact shape is unknown."""
        return self._http.send_request(method="POST", path="/user-onboarding/business-details", data=details)

    def subscribe_push(self, topics: list[str]) -> Any:
        """Subscribes the user to push notification topics."""
        return self._http.send_request(method="POST", path="/user-onboarding/subscribe-push", data={"topics": topics})
