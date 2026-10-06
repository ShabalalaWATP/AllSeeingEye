"""Refuse a stale or incomplete native shard before any test fixtures execute."""

from pathlib import Path

import pytest

from scripts.native_shard_manifest import (
    EXPRESSIONS,
    planned_ids,
    read_plan,
    require_identity,
    require_ids,
)

ROOT = Path(__file__).resolve().parents[1]
PLAN = pytest.StashKey[dict]()
EXPECTED = pytest.StashKey[list[str]]()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--native-plan", type=Path)
    parser.addoption("--native-plan-sha256")
    parser.addoption("--native-lane", choices=("parallel", "serial"))
    parser.addoption("--native-shard", type=int)
    parser.addoption("--native-shards", type=int)


def pytest_configure(config: pytest.Config) -> None:
    try:
        plan = read_plan(
            config.getoption("--native-plan"), config.getoption("--native-plan-sha256")
        )
        lane = config.getoption("--native-lane")
        parallel = lane == "parallel"
        if (
            config.option.markexpr != EXPRESSIONS[lane]
            or bool(config.option.isolated_postgres) != parallel
            or bool(config.option.owned_migrations) != parallel
            or bool(config.option.template_postgres) != parallel
            or (not parallel and getattr(config.option, "numprocesses", 0))
        ):
            raise ValueError("Native execution options differ from the collected lane")
        expected = planned_ids(
            plan,
            config.getoption("--native-lane"),
            config.getoption("--native-shard"),
            config.getoption("--native-shards"),
        )
        require_identity(plan, ROOT)
    except (OSError, TypeError, ValueError, AttributeError, KeyError) as error:
        raise pytest.UsageError("Native shard manifest or input identity is invalid") from error
    config.stash[PLAN] = plan
    config.stash[EXPECTED] = expected


def _check(config: pytest.Config, actual: list[str]) -> None:
    try:
        require_identity(config.stash[PLAN], ROOT)
        require_ids(config.stash[EXPECTED], actual)
    except (OSError, ValueError) as error:
        raise pytest.UsageError(
            "Native source/runtime/selection changed before execution"
        ) from error


def pytest_collection_finish(session: pytest.Session) -> None:
    # xdist's controller does not collect tests; every actual worker checks its
    # collection before sending IDs to the controller and entering runtestloop.
    if not hasattr(session.config, "workerinput") and getattr(
        session.config.option, "numprocesses", 0
    ):
        return
    _check(session.config, [item.nodeid for item in session.items])


def pytest_xdist_node_collection_finished(node, ids: list[str]) -> None:
    _check(node.config, ids)


@pytest.hookimpl(tryfirst=True)
def pytest_runtestloop(session: pytest.Session) -> None:
    # Recheck after every collection-finish hook, before fixture setup starts.
    pytest_collection_finish(session)
