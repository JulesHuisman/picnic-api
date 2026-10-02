import httpx
import pytest

from picnic_api import PicnicClient, PicnicError
from tests import samples
from tests.conftest import MockApi


def test_unauthenticated_contact_info_uses_the_public_api(client: PicnicClient, api: MockApi) -> None:
    api.queue_json(samples.CONTACT_INFO)

    info = client.customer_service.get_unauthenticated_contact_info(country_code="DE")

    assert str(api.last.url) == "https://storefront-prod.nl.picnicinternational.com/public-api/15/cs-contact-info"
    assert api.last.headers["picnic-country"] == "DE"
    assert "x-picnic-auth" not in api.last.headers
    assert info.opening_times["2026-10-02"].start == [8, 0]


def test_unauthenticated_contact_info_raises_on_errors(client: PicnicClient, api: MockApi) -> None:
    api.queue(httpx.Response(status_code=503))

    with pytest.raises(PicnicError, match="503 Service Unavailable"):
        client.customer_service.get_unauthenticated_contact_info(country_code="NL")
