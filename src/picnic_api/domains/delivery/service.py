from typing import Any

from pydantic import TypeAdapter

from picnic_api.domains.cart.models import DeliveryStatus
from picnic_api.domains.delivery.models import Delivery, DeliveryDetail, DeliveryPosition, DeliveryScenario
from picnic_api.http_client import HttpClient

DELIVERIES = TypeAdapter(list[Delivery])


class DeliveryService:
    """Delivery history, live position, ratings and invoices."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    async def get_deliveries(self, statuses: list[DeliveryStatus] | None = None) -> list[Delivery]:
        """Returns past and current deliveries, optionally filtered by status (e.g. `CURRENT`, `COMPLETED`)."""
        return DELIVERIES.validate_python(
            await self._http.send_request(method="POST", path="/deliveries/summary", data=statuses or [])
        )

    async def get_delivery(self, delivery_id: str) -> DeliveryDetail:
        """Returns the details of a delivery."""
        return DeliveryDetail.model_validate(
            obj=await self._http.send_request(method="GET", path=f"/deliveries/{delivery_id}")
        )

    async def get_delivery_position(self, delivery_id: str) -> DeliveryPosition:
        """Returns the live position of a delivery."""
        return DeliveryPosition.model_validate(
            obj=await self._http.send_request(
                method="GET", path=f"/deliveries/{delivery_id}/position", include_picnic_headers=True
            )
        )

    async def get_delivery_scenario(self, delivery_id: str) -> DeliveryScenario:
        """Returns the driver and route of a delivery."""
        return DeliveryScenario.model_validate(
            obj=await self._http.send_request(
                method="GET", path=f"/deliveries/{delivery_id}/scenario", include_picnic_headers=True
            )
        )

    async def cancel_delivery(self, delivery_id: str) -> Any:
        """Cancels the order of a delivery."""
        return await self._http.send_request(method="POST", path=f"/order/delivery/{delivery_id}/cancel")

    async def set_delivery_rating(self, delivery_id: str, rating: int) -> Any:
        """Rates a delivery from 0 to 10. The API answers 400 when the delivery is already rated."""
        return await self._http.send_request(
            method="POST", path=f"/deliveries/{delivery_id}/rating", data={"rating": rating}
        )

    async def send_delivery_invoice_email(self, delivery_id: str) -> Any:
        """(Re)sends the invoice email of a delivery."""
        return await self._http.send_request(method="POST", path=f"/deliveries/{delivery_id}/resend_invoice_email")
