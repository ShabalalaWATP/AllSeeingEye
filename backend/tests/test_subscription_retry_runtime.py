"""Worker retry classification never infers safety from an exception alone."""

from ase.container.subscription_retry_runtime import automatic_retry_payload, classify_failure
from ase.domain.errors import RateLimited
from ase.domain.subscription_retry import RetryFailure


def test_only_known_pre_dispatch_failures_retry_with_unchanged_ledger() -> None:
    saved = {"calls": [], "sections": {}}
    assert (
        classify_failure(ConnectionError(), "provider_error", saved, saved)
        is RetryFailure.TRANSIENT_PRE_DISPATCH
    )
    assert (
        classify_failure(RateLimited(300), "provider_error", saved, saved)
        is RetryFailure.RETRYABLE_RESPONSE
    )
    assert classify_failure(RuntimeError(), "provider_error", saved, saved) is None
    assert classify_failure(TimeoutError(), "time_limit", saved, saved) is None
    assert classify_failure(ConnectionError(), "provider_error", saved, {"calls": [{}]}) is None
    assert (
        classify_failure(
            ConnectionError(),
            "provider_error",
            saved,
            {"calls": [{"status": "in_flight"}]},
        )
        is RetryFailure.UNCERTAIN_PAID_CALL
    )
    assert (
        classify_failure(
            ConnectionError(),
            "provider_error",
            saved,
            {"calls": [{"status": "failed", "error": "provider_error"}]},
        )
        is None
    )


def test_retry_payload_preserves_completed_sections_and_resets_pre_dispatch_only() -> None:
    payload = {
        "calls": [],
        "sections": {
            "completed": {"status": "completed", "payload": {"body": "saved"}},
            "next": {"status": "running", "payload": {"kind": "topic"}},
        },
    }
    prepared = automatic_retry_payload(payload)
    assert prepared is not None
    assert prepared["sections"]["completed"] == payload["sections"]["completed"]
    assert prepared["sections"]["next"]["status"] == "incomplete"
    assert payload["sections"]["next"]["status"] == "running"
    assert automatic_retry_payload({"calls": [{"status": "uncertain"}]}) is None
    assert (
        automatic_retry_payload({"calls": [{"status": "failed", "error": "provider_error"}]})
        is None
    )
