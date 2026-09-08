"""Registration and retention for expanded public map observations."""

from ase.adapters.feeds.firms import SPEC
from ase.adapters.feeds.firms_public import PUBLIC_FIRMS, FirmsPublicConnector
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.feeds.satellites import SATELLITE_SPECS
from ase.application.feeds.budgets import DEFAULT_BUDGETS
from ase.domain.events import Category
from feeds_helpers import NOW, FakeClock, FakeHttp


def test_satellite_groups_and_public_firms_register_without_key():
    public_http = FakeHttp()
    connectors = build_connectors(FakeHttp(), FakeClock(NOW), public_firms_http=public_http)
    ids = [connector.spec.id for connector in connectors]
    assert len(ids) == len(set(ids))
    assert {spec.id for spec in SATELLITE_SPECS} <= set(ids)
    public = next(connector for connector in connectors if connector.spec.id == PUBLIC_FIRMS.id)
    assert isinstance(public, FirmsPublicConnector)
    assert public.http is public_http
    assert SPEC.id not in ids


def test_operator_key_and_explicit_public_disable_prevent_duplicate_collection():
    for options in ({"firms_key": "synthetic_key_123456789"}, {"include_public_firms": False}):
        ids = {c.spec.id for c in build_connectors(FakeHttp(), FakeClock(NOW), **options)}
        assert PUBLIC_FIRMS.id not in ids
    disabled = (PUBLIC_FIRMS.id, SATELLITE_SPECS[1].id)
    ids = {c.spec.id for c in build_connectors(FakeHttp(), FakeClock(NOW), disabled)}
    assert not set(disabled) & ids


def test_space_retention_can_hold_the_bounded_active_catalogue():
    assert DEFAULT_BUDGETS[Category.SPACE].max_items == 25_000
