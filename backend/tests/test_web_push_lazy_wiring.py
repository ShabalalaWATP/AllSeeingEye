"""Optional push imports preserve real configured construction and worker lifecycle."""

import asyncio
import base64
import json
import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from py_vapid import Vapid
from pydantic import SecretStr

from ase.container.web_push import push_sender, run_web_push, web_push_service
from ase.domain.errors import InvalidRequest
from ase.domain.web_push import PushSubscription

FRESH_APP = """
import asyncio, json, sys
from uvicorn.importer import import_from_string
app = import_from_string('ase.main:app')
import ase.container.web_push as wiring
def loaded():
    return sorted(name for name in sys.modules if
        name == 'ase.adapters.notify.web_push'
        or name.split('.')[0] in {'pywebpush', 'py_vapid'})
def forbidden_store(*args):
    raise AssertionError('Unconfigured worker accessed its delivery store')
wiring.SqlPushDeliveryStore = forbidden_store
before = loaded()
async def check():
    worker = asyncio.create_task(wiring.run_web_push(app.state.container))
    try:
        await asyncio.sleep(0)
        assert not worker.done(), 'Unconfigured worker did not remain idle'
        worker.cancel()
        outcomes = await asyncio.gather(worker, return_exceptions=True)
        after_idle = loaded()
        from ase.domain.errors import InvalidRequest
        from ase.domain.web_push import PushSubscription
        async with app.state.container.session_factory() as session:
            service = wiring.web_push_service(app.state.container, session)
            try:
                await service._validator.validate(PushSubscription('http://127.0.0.1/', '', ''))
            except InvalidRequest as error:
                assert str(error) == 'Push endpoints require public HTTPS on port 443.'
            else:
                raise AssertionError('Cold request validator accepted an unsafe endpoint')
        assert {'ase.adapters.notify.web_push', 'pywebpush', 'py_vapid'} <= set(loaded())
    finally:
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)
        await app.state.container.dispose()
    assert isinstance(outcomes[0], asyncio.CancelledError)
    assert not any(task is not asyncio.current_task() and not task.done()
                   for task in asyncio.all_tasks())
    print(json.dumps({'before': before, 'after': after_idle, 'cold_validator': True,
                      'cancelled': True, 'disposed': True}))
asyncio.run(check())
"""


def test_fresh_asgi_import_and_unconfigured_worker_do_not_load_push_transport(tmp_path):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("ASE_")}
    environment.update(
        ASE_ENV="test",
        ASE_DATABASE_URL="sqlite+aiosqlite://",
        ASE_FEEDS_ENABLED="false",
    )
    # Only the current interpreter and literal regression program are executed.
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-c", FRESH_APP],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    observed = json.loads(completed.stdout.splitlines()[-1])
    assert observed == {
        "before": [],
        "after": [],
        "cold_validator": True,
        "cancelled": True,
        "disposed": True,
    }


def configured_container(key, subject="mailto:operator@example.invalid", *, available=True):
    return SimpleNamespace(
        settings=SimpleNamespace(web_push_vapid_private_key=key, web_push_vapid_subject=subject),
        cipher=SimpleNamespace(available=available),
    )


@pytest.mark.parametrize(
    "key,subject,available",
    [
        (None, None, True),
        (None, "mailto:operator@example.invalid", True),
        (SecretStr("invalid-fixture-key"), None, True),
        (SecretStr("invalid-fixture-key"), "mailto:operator@example.invalid", False),
    ],
)
def test_unavailable_configurations_do_not_construct_a_sender(monkeypatch, key, subject, available):
    constructor = Mock(side_effect=AssertionError("Unavailable push constructed a sender"))
    monkeypatch.setattr("ase.adapters.notify.web_push.WebPushSender", constructor)
    assert push_sender(configured_container(key, subject, available=available)) is None
    constructor.assert_not_called()


def private_key():
    key = ec.generate_private_key(ec.SECP256R1())
    encoded = base64.urlsafe_b64encode(
        key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
    ).decode()
    public = (
        base64.urlsafe_b64encode(
            key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        )
        .rstrip(b"=")
        .decode()
    )
    return SecretStr(encoded), public


def test_configured_sender_retains_real_public_key():
    key, public = private_key()
    sender = push_sender(configured_container(key))
    assert sender is not None
    assert type(sender).__module__ == "ase.adapters.notify.web_push"
    assert sender.public_key == public


async def test_configured_worker_constructs_sender_before_store_and_cancels(monkeypatch):
    key, public = private_key()
    container = configured_container(key)
    container.session_factory = object()
    container.access_policy = object()
    container.clock = object()
    started = asyncio.Event()
    seen = []

    class Worker:
        def __init__(self, store, sender, clock):
            assert store == "store" and clock is container.clock
            assert sender.public_key == public
            seen.append("constructed")

        async def run(self):
            seen.append("running")
            started.set()
            await asyncio.Event().wait()

    monkeypatch.setattr("ase.container.web_push.SqlPushDeliveryStore", lambda *args: "store")
    monkeypatch.setattr("ase.container.web_push.WebPushWorker", Worker)
    task = asyncio.create_task(run_web_push(container))
    try:
        await asyncio.wait_for(started.wait(), timeout=5)
        assert seen == ["constructed", "running"]
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    assert task.cancelled()


async def test_invalid_configured_key_fails_before_delivery_store(monkeypatch):
    container = configured_container(SecretStr("invalid-fixture-key"))
    # Compare the real library's failure contract without pinning a library-internal class.
    with pytest.raises(Exception) as expected:
        Vapid.from_string("invalid-fixture-key")
    store = Mock(side_effect=AssertionError("Invalid key reached delivery admission"))
    monkeypatch.setattr("ase.container.web_push.SqlPushDeliveryStore", store)
    with pytest.raises(type(expected.value)) as actual:
        await run_web_push(container)
    assert str(actual.value) == str(expected.value)
    store.assert_not_called()


async def test_request_composition_retains_real_endpoint_validator(container, monkeypatch):
    async def forbidden_dns(_url):
        raise AssertionError("Invalid endpoint should be rejected before DNS")

    monkeypatch.setattr("ase.adapters.notify.web_push.assert_public_host", forbidden_dns)
    async with container.session_factory() as session:
        service = web_push_service(container, session)
        with pytest.raises(InvalidRequest, match="public HTTPS"):
            await service._validator.validate(PushSubscription("http://127.0.0.1/", "", ""))
