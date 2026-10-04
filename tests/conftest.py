import inspect
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx
import pytest

from picnic_api import PicnicClient

type Reply = httpx.Response | Callable[[httpx.Request], httpx.Response | Awaitable[httpx.Response]]

AUTH_KEY = "initial-auth-key"
BASE_URL = "https://storefront-prod.nl.picnicinternational.com/api/15"


class MockApi:
    """An httpx transport handler that records requests and answers with queued replies (default `{}`)."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.replies: list[Reply] = []
        self.fallback: Reply = lambda request: httpx.Response(status_code=200, json={})

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        reply = self.replies.pop(0) if self.replies else self.fallback
        response = reply if isinstance(reply, httpx.Response) else reply(request)
        return await response if inspect.isawaitable(response) else response

    def queue(self, *replies: Reply) -> None:
        """Queues replies for the next requests."""
        self.replies.extend(replies)

    def queue_json(self, *payloads: Any) -> None:
        """Queues JSON 200 replies for the next requests."""
        self.queue(*(httpx.Response(status_code=200, json=payload) for payload in payloads))

    @property
    def last(self) -> httpx.Request:
        """The most recent request."""
        return self.requests[-1]

    def last_json(self) -> Any:
        """The JSON body of the most recent request."""
        return json.loads(self.last.content)


@pytest.fixture
def api() -> MockApi:
    return MockApi()


@pytest.fixture
async def client(api: MockApi) -> AsyncIterator[PicnicClient]:
    session = httpx.AsyncClient(transport=httpx.MockTransport(handler=api))
    async with PicnicClient(auth_key=AUTH_KEY, session=session) as picnic:
        yield picnic
