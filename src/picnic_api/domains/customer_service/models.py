from typing import Literal

from picnic_api.models.common import PicnicModel
from picnic_api.models.fusion import PmlDocument

type MessageDisplayPosition = Literal["PROMPT", "MESSAGE_BAR", "ORDER_CONFIRMATION", "STOREFRONT_DIALOG", "UNSUPPORTED"]

type ReminderDayOfWeek = Literal["EMPTY", "SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]


class OpeningTime(PicnicModel):
    """Opening hours as `[hour, minute]` pairs."""

    start: list[int]
    end: list[int]


class ContactDetails(PicnicModel):
    email: str
    phone: str
    whatsapp: str


class CustomerServiceContactInfo(PicnicModel):
    """Contact details plus opening times keyed by date (e.g. "2026-02-25")."""

    contact_details: ContactDetails
    opening_times: dict[str, OpeningTime]


class Message(PicnicModel):
    """An in-app message (popup, banner, order-confirmation card). Times are Unix milliseconds."""

    display_position: MessageDisplayPosition
    send_correlation_id: str
    sent_time: int
    expiry_time: int
    user_id: str
    target_entity_id: str | None
    content: PmlDocument


class MessagesWrapper(PicnicModel):
    """Response of `/messages`. `query_interval` is the polling interval in milliseconds."""

    messages: list[Message]
    query_interval: int | None


class Reminder(PicnicModel):
    """A delivery reminder. `time_of_day` is `[hour, minute]`."""

    day_of_week: ReminderDayOfWeek | None
    time_of_day: list[int] | None


class RemindersWrapper(PicnicModel):
    reminders: list[Reminder]


class ParcelCurrentStatus(PicnicModel):
    status: str
    timestamp: str


class Parcel(PicnicModel):
    """A parcel shipped by an external carrier. `id` is the carrier tracking code."""

    id: str
    handler_name: str
    active: bool
    current_status: ParcelCurrentStatus
