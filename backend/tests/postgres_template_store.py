"""Owned, disposable PostgreSQL templates and per-test databases, never shared state."""

import asyncio
import re
from dataclasses import dataclass, field
from uuid import uuid4

import asyncpg
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine

from ase.adapters.persistence.session import create_engine
from postgres_template_guard import instrumented, schema_fingerprint
from pytest_support import create_schema


@dataclass
class TemplateDatabase:
    name: str
    url: str = field(repr=False)
    fingerprint: str
    reset: bool = False

    def unchanged(self, engine: AsyncEngine) -> bool:
        if engine.url != make_url(self.url):
            raise ValueError("The app engine does not target its owned template clone")
        return not instrumented(engine) and schema_fingerprint() == self.fingerprint

    async def prepare(self, engine: AsyncEngine) -> None:
        if not self.unchanged(engine):
            self.reset = True
            await create_schema(engine, fresh=False)

    def requires_drop(self, engine: AsyncEngine) -> bool:
        unchanged = self.unchanged(engine)  # Always validate ownership, including after fallback.
        return self.reset or not unchanged


class TemplateWorker:
    """A worker owns its template and every successfully created child by exact name."""

    def __init__(self, worker_url: str, fingerprint: str | None) -> None:
        parsed = make_url(worker_url)
        if (
            parsed.get_backend_name() != "postgresql"
            or parsed.host not in {"localhost", "127.0.0.1", "::1"}
            or parsed.query
            or not re.fullmatch(r"ase_test_[a-f0-9]{32}_(?:gw[0-9]+|master)", parsed.database or "")
        ):
            raise ValueError("Templates require an owned local PostgreSQL worker database")
        self._service = parsed.set(drivername="postgresql")
        self._application = parsed.set(drivername="postgresql+asyncpg")
        self.fingerprint = fingerprint
        self.template: str | None = None
        self._allocated: set[str] = set()
        self._created: set[str] = set()
        self._leases: dict[str, TemplateDatabase] = {}

    def _allocate(self) -> str:
        name = f"ase_template_{uuid4().hex}"
        self._allocated.add(name)
        return name

    def _url(self, name: str) -> str:
        self._validate(name)
        return self._application.set(database=name).render_as_string(hide_password=False)

    def _validate(self, name: str) -> None:
        if name not in self._allocated or not re.fullmatch(r"ase_template_[a-f0-9]{32}", name):
            raise ValueError("Refusing an unowned template database")

    async def _command(
        self, name: str, *, clone: bool = False, drop: bool = False, seal: bool = False
    ) -> None:
        # Finish acknowledgement and ownership bookkeeping before propagating cancellation.
        # Otherwise CREATE could succeed on the server while the caller forgets its name.
        operation = asyncio.create_task(self._execute(name, clone=clone, drop=drop, seal=seal))
        try:
            await asyncio.shield(operation)
        except asyncio.CancelledError:
            await operation
            raise

    async def _execute(self, name: str, *, clone: bool, drop: bool, seal: bool) -> None:
        self._validate(name)
        if (drop or seal) and name not in self._created:
            raise ValueError("Refusing to drop a database this worker did not create")
        connection = await asyncpg.connect(
            self._service.render_as_string(hide_password=False), command_timeout=10
        )
        try:
            if seal:
                verb = "ALTER"
                await connection.execute(f'{verb} DATABASE "{name}" ALLOW_CONNECTIONS false')
                return
            verb = "DROP" if drop else "CREATE"
            suffix = ""
            if clone:
                if self.template is None or self.template not in self._created:
                    raise ValueError("No owned template is available")
                self._validate(self.template)
                # No force-disconnect: a live template connection is an isolation bug.
                active = await connection.fetchval(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=$1", self.template
                )
                if active:
                    raise RuntimeError("Template still has database connections")
                suffix = f' TEMPLATE "{self.template}"'
            await connection.execute(f'{verb} DATABASE "{name}"{suffix}')
            if drop:
                self._created.remove(name)
                self._leases.pop(name, None)
            else:
                self._created.add(name)
        finally:
            await connection.close()

    async def acquire(self) -> TemplateDatabase | None:
        if not self.fingerprint or schema_fingerprint() != self.fingerprint:
            return None
        if self.template is None:
            name = self._allocate()
            engine = create_engine(self._url(name))
            try:
                if instrumented(engine):
                    return None
                await self._command(name)
                await create_schema(engine, fresh=True)
            finally:
                await engine.dispose()
            # Prevent accidental future writes to the warm template itself.
            await self._command(name, seal=True)
            self.template = name
        if schema_fingerprint() != self.fingerprint:
            return None
        name = self._allocate()
        await self._command(name, clone=True)
        database = TemplateDatabase(name, self._url(name), self.fingerprint)
        self._leases[name] = database
        return database

    async def release(self, database: TemplateDatabase) -> None:
        if self._leases.get(database.name) is not database:
            raise ValueError("A test can release only its own active template lease")
        await self._command(database.name, drop=True)

    async def close(self) -> None:
        # Attempt every owned cleanup even if one leaking test prevents its own drop.
        errors = []
        names = sorted(self._created, key=lambda name: name == self.template)
        for name in names:
            try:
                await self._command(name, drop=True)
            except Exception as error:  # Report cleanup failure; never terminate other connections.
                errors.append(error)
        if errors:
            raise ExceptionGroup("Owned PostgreSQL template cleanup failed", errors)
