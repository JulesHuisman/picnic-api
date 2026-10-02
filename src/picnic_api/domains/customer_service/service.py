from urllib.parse import urlencode

from pydantic import TypeAdapter

from picnic_api.domains.customer_service.models import (
    CustomerServiceContactInfo,
    MessageDisplayPosition,
    MessagesWrapper,
    Parcel,
    Reminder,
    RemindersWrapper,
)
from picnic_api.errors import PicnicError
from picnic_api.http_client import HttpClient, describe_error

PARCELS = TypeAdapter(list[Parcel])


class CustomerServiceService:
    """Contact info, messages, reminders and parcels."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def get_contact_info(self) -> CustomerServiceContactInfo:
        """Returns customer service contact details and opening times."""
        return CustomerServiceContactInfo.model_validate(
            obj=self._http.send_request(method="GET", path="/cs-contact-info", include_picnic_headers=True)
        )

    def get_messages(self, display_positions: list[MessageDisplayPosition] | None = None) -> MessagesWrapper:
        """Returns in-app messages, optionally filtered by display position."""
        query = f"?{urlencode(query=[('display_position', p) for p in display_positions])}" if display_positions else ""
        return MessagesWrapper.model_validate(
            obj=self._http.send_request(method="GET", path=f"/messages{query}", include_picnic_headers=True)
        )

    def get_reminders(self) -> RemindersWrapper:
        """Returns the user's delivery reminders. Reminders do not seem to be working on Picnic's side yet."""
        return RemindersWrapper.model_validate(
            obj=self._http.send_request(method="GET", path="/reminders", include_picnic_headers=True)
        )

    def set_reminders(self, reminders: list[Reminder]) -> None:
        """Replaces the user's delivery reminders. Reminders do not seem to be working on Picnic's side yet."""
        self._http.send_request(
            method="PUT",
            path="/reminders",
            data=[reminder.model_dump() for reminder in reminders],
            include_picnic_headers=True,
        )

    def get_parcels(self) -> list[Parcel]:
        """Returns parcels shipped by external carriers."""
        return PARCELS.validate_python(
            self._http.send_request(method="GET", path="/parcels", include_picnic_headers=True)
        )

    def get_unauthenticated_contact_info(self, country_code: str) -> CustomerServiceContactInfo:
        """Returns contact info without authentication, from the public API for the given country."""
        public_url = self._http.url.replace("/api/", "/public-api/")
        response = self._http.session.get(url=f"{public_url}/cs-contact-info", headers={"picnic-country": country_code})
        if response.is_error:
            raise PicnicError(describe_error(response=response))
        return CustomerServiceContactInfo.model_validate(obj=response.json())
