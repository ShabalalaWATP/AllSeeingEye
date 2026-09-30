"""Template eligibility and ownership fail closed without touching a database."""

from types import SimpleNamespace

import pytest
from sqlalchemy import Column, Connection, Integer, MetaData, Table, event

import postgres_template_guard as guard
from ase.adapters.persistence.session import create_engine
from postgres_template_store import TemplateDatabase, TemplateWorker


@pytest.fixture
def metadata(monkeypatch):
    result = MetaData()
    Table("example", result, Column("id", Integer, primary_key=True))
    monkeypatch.setattr(guard, "Base", SimpleNamespace(metadata=result))
    monkeypatch.setattr(guard, "_METADATA", result)
    return result


def test_schema_and_ddl_listeners_invalidate_eligibility(metadata):
    before = guard.schema_fingerprint()
    assert before
    column = metadata.tables["example"].c.id
    column.nullable = True
    assert guard.schema_fingerprint() != before
    column.nullable = False
    assert guard.schema_fingerprint() == before

    def observe(*_args, **_kwargs):
        pass

    for target in (metadata, metadata.tables["example"]):
        for name in guard.DDL_EVENTS:
            event.listen(target, name, observe)
            try:
                assert guard.schema_fingerprint() is None
            finally:
                event.remove(target, name, observe)


async def test_engine_observer_requires_normal_ddl():
    engine = create_engine("sqlite+aiosqlite://")

    def observe(*_args, **_kwargs):
        pass

    try:
        assert not guard.instrumented(engine)
        event.listen(engine.sync_engine, "before_cursor_execute", observe)
        assert guard.instrumented(engine)
        event.remove(engine.sync_engine, "before_cursor_execute", observe)
        assert not guard.instrumented(engine)
    finally:
        await engine.dispose()


@pytest.mark.parametrize("options", [{}, {"named": True}, {"once": True}])
async def test_custom_pool_hooks_including_sqlalchemy_wrappers_require_fallback(options):
    engine = create_engine("sqlite+aiosqlite://")

    def observe(*_args, **_kwargs):
        pass

    try:
        event.listen(engine.sync_engine.pool, "connect", observe, **options)
        assert guard.instrumented(engine)
    finally:
        await engine.dispose()


async def test_class_connection_observers_require_fallback(monkeypatch):
    engine = create_engine("sqlite+aiosqlite://")
    monkeypatch.setattr(Connection, "_has_events", False, raising=False)

    def observe(*_args, **_kwargs):
        pass

    event.listen(Connection, "before_execute", observe)
    try:
        assert guard.instrumented(engine)
    finally:
        event.remove(Connection, "before_execute", observe)
        await engine.dispose()


@pytest.mark.parametrize("reset", [False, True])
async def test_even_fallback_teardown_refuses_a_foreign_engine(reset):
    engine = create_engine("sqlite+aiosqlite://")
    database = TemplateDatabase("owned", "sqlite+aiosqlite:///other.sqlite", "digest", reset)
    try:
        with pytest.raises(ValueError, match="owned template clone"):
            await database.prepare(engine)
        with pytest.raises(ValueError, match="owned template clone"):
            database.requires_drop(engine)
    finally:
        await engine.dispose()


@pytest.mark.parametrize(
    "url",
    [
        "sqlite://",
        "postgresql+asyncpg://remote.example/ase_test_" + "a" * 32 + "_master",
        "postgresql+asyncpg://localhost/operator_database",
        "postgresql+asyncpg://localhost/ase_test_" + "a" * 32 + "_master?host=remote.example",
        "postgresql+asyncpg://localhost/ase_test_" + "a" * 32 + "_master?database=operator",
    ],
)
def test_only_plain_owned_loopback_worker_urls_are_allowed(url):
    with pytest.raises(ValueError, match="owned local"):
        TemplateWorker(url, "digest")


async def test_unowned_names_and_forged_leases_never_reach_sql(monkeypatch):
    worker = TemplateWorker("postgresql+asyncpg://localhost/ase_test_" + "a" * 32 + "_master", "x")

    async def forbidden(*_args, **_kwargs):
        pytest.fail("An invalid ownership request connected to PostgreSQL")

    monkeypatch.setattr("postgres_template_store.asyncpg.connect", forbidden)
    with pytest.raises(ValueError, match="unowned"):
        await worker._command("ase_template_" + "b" * 32, drop=True)
    allocated = worker._allocate()
    with pytest.raises(ValueError, match="did not create"):
        await worker._command(allocated, drop=True)
    with pytest.raises(ValueError, match="active template lease"):
        await worker.release(TemplateDatabase(allocated, worker._url(allocated), "x"))


def test_effective_fixture_overrides_special_lanes_and_direct_factories_fall_back(
    monkeypatch, tmp_path
):
    def app():
        pass

    def settings():
        pass

    def custom():
        pass

    def direct():
        create_engine("sqlite+aiosqlite://")

    monkeypatch.setattr(guard, "_DEFAULTS", {"app": app, "settings": settings})
    source = tmp_path / "test_ordinary.py"
    source.write_text("def test_read(): pass\n")
    definitions = {
        "app": [SimpleNamespace(func=app)],
        "settings": [SimpleNamespace(func=settings)],
    }
    item = SimpleNamespace(
        path=source,
        obj=lambda: None,
        _fixtureinfo=SimpleNamespace(name2fixturedefs=definitions),
        get_closest_marker=lambda _name: None,
    )
    assert guard.ordinary_app(item)
    for name in ("settings", "app"):
        definitions[name].append(SimpleNamespace(func=custom))
        assert not guard.ordinary_app(item)
        definitions[name].pop()
    definitions["secondary"] = [SimpleNamespace(func=direct)]
    assert not guard.ordinary_app(item)
    definitions.pop("secondary")
    for marker in ("race", "migration", "postgres"):
        item.get_closest_marker = lambda name, expected=marker: name == expected
        assert not guard.ordinary_app(item)
    item.get_closest_marker = lambda name: name == "db"
    assert guard.ordinary_app(item)  # Ordinary persistence selection remains eligible.
