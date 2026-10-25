"""Shared test setup.

optimizer.py builds Google API clients at import time, which needs credentials.
Swap the constructors for dummies *before* it is imported anywhere; each test
then installs the fake it needs with the `fake_routes` / `fake_places` /
`fake_nrel` fixtures. Nothing here talks to the network.
"""

import asyncio

import pytest
from google.maps import places_v1, routing_v2

routing_v2.RoutesClient = lambda *a, **k: object()
places_v1.PlacesClient = lambda *a, **k: object()

from app.core.config import settings  # noqa: E402
from app.services import optimizer  # noqa: E402
from tests import factories  # noqa: E402


@pytest.fixture
def fake_routes(monkeypatch):
    fake = factories.FakeRoutesClient()
    monkeypatch.setattr(optimizer, "client", fake)
    return fake


@pytest.fixture
def fake_places(monkeypatch):
    fake = factories.FakePlacesClient()
    monkeypatch.setattr(optimizer, "places_client", fake)
    return fake


@pytest.fixture
def fake_nrel(monkeypatch):
    fake = factories.FakeNrel()
    monkeypatch.setattr(optimizer.requests, "post", fake.post)
    monkeypatch.setattr(settings, "nrel_api_key", "TEST_KEY")
    return fake


@pytest.fixture
def no_delay(monkeypatch):
    """optimize() sleeps ~2.4s to simulate provider latency; skip that."""
    real_sleep = asyncio.sleep

    async def instant(_seconds):
        await real_sleep(0)

    monkeypatch.setattr(optimizer.asyncio, "sleep", instant)


@pytest.fixture(autouse=True)
def fresh_places_state():
    """The Places cache and rate limiter are module-level; keep tests independent."""
    optimizer._clear_places_state()
    yield
    optimizer._clear_places_state()
