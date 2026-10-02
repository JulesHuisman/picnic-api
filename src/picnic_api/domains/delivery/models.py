from typing import Any, Literal

from picnic_api.domains.cart.models import DeliverySlot, DeliveryStatus, Order
from picnic_api.models.common import PicnicModel


class DeliveryTime(PicnicModel):
    start: str
    end: str


class DeliveryOrder(PicnicModel):
    """Slim order summary in the deliveries list. `DeliveryService.get_delivery` returns the full `Order`."""

    type: Literal["ORDER"]
    id: str
    creation_time: str
    total_price: int
    status: DeliveryStatus
    cancellation_time: str | None


class Delivery(PicnicModel):
    delivery_id: str
    creation_time: str
    slot: DeliverySlot
    eta2: DeliveryTime
    status: DeliveryStatus
    delivery_time: DeliveryTime
    orders: list[DeliveryOrder]


class ReturnedContainer(PicnicModel):
    type: str
    localized_name: str
    quantity: int
    price: int


class DeliveryDetail(PicnicModel):
    """Full delivery detail with complete orders, returned containers and parcels."""

    type: Literal["DELIVERY"]
    id: str
    delivery_id: str
    creation_time: str
    slot: DeliverySlot
    eta2: DeliveryTime
    status: DeliveryStatus
    delivery_time: DeliveryTime
    orders: list[Order]
    returned_containers: list[ReturnedContainer]
    parcels: list[Any]


class Vehicle(PicnicModel):
    """A delivery vehicle. `image` is base64 encoded."""

    image: str
    name: str | None = None


class DeliveryDriver(PicnicModel):
    name: str
    photo_url: str | None = None


class DeliveryAddress(PicnicModel):
    id: str | None = None
    postcode: str
    house_number: int
    house_number_extension: str | None = None
    street: str | None = None
    city: str | None = None


class ScenarioEntry(PicnicModel):
    """A point on the delivery route. `ts` is Unix milliseconds."""

    ts: int
    lat: float
    lng: float


class DeliveryScenario(PicnicModel):
    version: int
    scenario: list[ScenarioEntry]
    vehicle: Vehicle
    driver: DeliveryDriver | None = None
    trailers: list[Vehicle] | None = None
    destination: DeliveryAddress | None = None


class DeliveryPosition(PicnicModel):
    """Live delivery position. Timestamps and `query_interval` are in milliseconds."""

    version: int
    scenario_ts: int
    eta: int
    eta_window: DeliveryTime
    query_interval: int
    scenario_in_progress: bool
