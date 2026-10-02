import httpx
import pytest

from picnic_api import PicnicClient, UnexpectedPageFormatError
from picnic_api.domains.app.models import DeeplinkResolution
from picnic_api.domains.app.rsc import parse_rsc_payload
from tests import samples
from tests.conftest import BASE_URL, MockApi

RSC_PAYLOAD = "\n".join(
    [
        '0:{"_value":"$L1"}',
        '2:I["./components/page/page-hydrator.tsx",["chunk-a"],"PageHydrator"]',
        '1:["$","$L2",null,{"children":"$L7"}]',
        '7:["$","$L8",null,{"items":[{"title":"Alle acties"}],"name":"category-tree"}]',
    ]
)


def rsc_response() -> httpx.Response:
    return httpx.Response(status_code=200, text=RSC_PAYLOAD, headers={"content-type": "text/x-component"})


def test_parse_rsc_payload_splits_rows_and_modules() -> None:
    page = parse_rsc_payload(payload=RSC_PAYLOAD)

    assert page.rows["0"] == {"_value": "$L1"}
    assert page.rows["7"] == ["$", "$L8", None, {"items": [{"title": "Alle acties"}], "name": "category-tree"}]
    assert page.modules["2"] == ["./components/page/page-hydrator.tsx", ["chunk-a"], "PageHydrator"]
    assert "2" not in page.rows


def test_parse_rsc_payload_skips_non_json_rows_and_non_rows() -> None:
    page = parse_rsc_payload(
        payload="\n".join(['a:HL["/style.css","style"]', "3:T5,hello", "not a row", "", '1f:{"ok":true}'])
    )

    assert page.rows == {"1f": {"ok": True}}
    assert page.modules == {}


def test_get_page_returns_a_fusion_page(client: PicnicClient, api: MockApi) -> None:
    api.queue_json(samples.FUSION_PAGE)

    page = client.app.get_page(page_id="home_page_root")

    assert page.layout.id == "home_page_root"
    assert str(api.last.url) == f"{BASE_URL}/pages/home_page_root"
    assert "x-picnic-agent" in api.last.headers


def test_get_page_accepts_a_bare_layout(client: PicnicClient, api: MockApi) -> None:
    api.queue_json(samples.FUSION_PAGE["layout"])

    page = client.app.get_page(page_id="home_page_root")

    assert page.layout.id == "home_page_root"
    assert page.script == {}


def test_get_page_rejects_rsc_pages(client: PicnicClient, api: MockApi) -> None:
    api.queue(rsc_response())

    with pytest.raises(UnexpectedPageFormatError) as error:
        client.app.get_page(page_id="category-tree-root")

    assert (error.value.page_id, error.value.received_format) == ("category-tree-root", "rsc")


def test_get_rsc_page_parses_the_payload(client: PicnicClient, api: MockApi) -> None:
    api.queue(rsc_response())

    page = client.app.get_rsc_page(page_id="category-tree-root")

    assert page.rows["7"][3]["name"] == "category-tree"
    assert page.modules


def test_get_rsc_page_rejects_fusion_pages(client: PicnicClient, api: MockApi) -> None:
    api.queue_json(samples.FUSION_PAGE)

    with pytest.raises(UnexpectedPageFormatError) as error:
        client.app.get_rsc_page(page_id="home_page_root")

    assert error.value.received_format == "fusion"


def test_bootstrap_and_deeplink_models(client: PicnicClient, api: MockApi) -> None:
    api.queue_json(samples.BOOTSTRAP, {"url": "picnic://home"})

    bootstrap = client.app.get_bootstrap_data()
    deeplink = client.app.resolve_deeplink(url="https://picnic.app/nl/deeplink/home")

    assert bootstrap.tabs[0].target is not None
    assert bootstrap.tabs[0].target.reference == "home_page_root"
    assert bootstrap.datadog_config is not None
    assert bootstrap.datadog_config.rum_session_sample_rate == 0.5
    assert deeplink == DeeplinkResolution(url="picnic://home")
