"""Listener presence must stay conservative without materialising known collections."""

from types import SimpleNamespace

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, event
from sqlalchemy.event.attr import _EmptyListener, _JoinedListener, _ListenerCollection

import postgres_template_guard as guard


class FalseyCallback:
    def __bool__(self):
        return False

    def __call__(self, *_args, **_kwargs):
        pytest.fail("A fingerprint must not execute a DDL listener")


@pytest.fixture
def metadata(monkeypatch):
    result = MetaData()
    Table("example", result, Column("id", Integer, primary_key=True))
    monkeypatch.setattr(guard, "Base", SimpleNamespace(metadata=result))
    monkeypatch.setattr(guard, "_METADATA", result)
    return result


@pytest.mark.parametrize("scope", ["empty", "instance", "parent", "joined"])
def test_real_listener_presence_keeps_exact_type_iteration_contract(metadata, monkeypatch, scope):
    original = guard.schema_fingerprint()
    callback = FalseyCallback()
    parent = MetaData()
    target = {"empty": None, "instance": metadata, "parent": MetaData, "joined": parent}[scope]
    if target is not None:
        event.listen(target, "after_create", callback)
    if scope == "joined":
        monkeypatch.setattr(metadata, "dispatch", metadata.dispatch._join(parent.dispatch))
        assert type(metadata.dispatch.after_create) is _JoinedListener
    iterations = []

    def count_iteration(original_iterator, collection):
        iterations.append(type(collection))
        return original_iterator(collection)

    try:
        for collection_type in (_EmptyListener, _ListenerCollection, _JoinedListener):
            original_iterator = collection_type.__iter__

            def counted(collection, original_iterator=original_iterator):
                return count_iteration(original_iterator, collection)

            monkeypatch.setattr(collection_type, "__iter__", counted)
        assert guard.schema_fingerprint() == (original if scope == "empty" else None)
        assert bool(iterations) is (scope == "joined")
        if scope == "joined":
            assert _JoinedListener in iterations
        if target is not None:
            event.remove(target, "after_create", callback)
            target = None
            iterations.clear()
            assert guard.schema_fingerprint() == original
            assert bool(iterations) is (scope == "joined")
    finally:
        if target is not None:
            event.remove(target, "after_create", callback)


def install_dispatch(monkeypatch, dispatch):
    metadata = SimpleNamespace(tables={}, _sequences={}, dispatch=dispatch)
    monkeypatch.setattr(guard, "Base", SimpleNamespace(metadata=metadata))
    monkeypatch.setattr(guard, "_METADATA", metadata)


def test_unknown_falsey_collection_keeps_complete_tuple_evaluation(monkeypatch):
    observed = []

    class UnknownCollection:
        def __bool__(self):
            return False

        def __len__(self):
            return 0

        def __iter__(self):
            for value in (None, FalseyCallback(), FalseyCallback()):
                observed.append(value)
                yield value

    install_dispatch(monkeypatch, SimpleNamespace(before_create=UnknownCollection()))
    assert guard.schema_fingerprint() is None
    assert len(observed) == 3


def test_unknown_iterator_exception_is_not_hidden_after_first_listener(monkeypatch):
    failure = RuntimeError("synthetic listener iterator failure")

    def listeners():
        yield FalseyCallback()
        raise failure

    install_dispatch(monkeypatch, SimpleNamespace(before_create=listeners()))
    with pytest.raises(RuntimeError) as caught:
        guard.schema_fingerprint()
    assert caught.value is failure


def test_known_collection_subclass_keeps_original_iteration(monkeypatch):
    observed = []

    class ChangedCollection(_ListenerCollection):
        def __len__(self):
            return 0

        def __iter__(self):
            observed.append("subclass")
            yield FalseyCallback()

    empty = MetaData().dispatch.before_create
    listeners = ChangedCollection(empty.parent, MetaData)
    install_dispatch(monkeypatch, SimpleNamespace(before_create=listeners))
    assert guard.schema_fingerprint() is None
    assert observed == ["subclass"]


def test_event_order_and_first_nonempty_rejection_remain_exact(monkeypatch):
    observed = []

    class Dispatch:
        def __getattr__(self, name):
            observed.append(name)
            if name == "before_create":
                return ()
            if name == "after_create":
                return (FalseyCallback(),)
            pytest.fail("The original scan stops at its first nonempty event")

    install_dispatch(monkeypatch, Dispatch())
    assert guard.schema_fingerprint() is None
    assert observed == ["before_create", "after_create"]
