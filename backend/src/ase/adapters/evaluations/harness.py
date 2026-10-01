"""The packaged casebooks behind the administrator evaluation port.

Each case runs through ``evaluate_case`` and the real Producer, with the caller's
metered gateway. The artefact mirrors the CLI output directory as a zip: the
results, an unlabelled human review template and one Markdown report per case.
It never includes the connection's base URL or key, and provider error text is
replaced by a fixed label because it is not under this application's control.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime
from functools import cached_property
from typing import Any

from ase.adapters.evaluations.casebook import CASEBOOKS, EvaluationCase, packaged_cases
from ase.adapters.evaluations.human_review import review_template
from ase.adapters.evaluations.pipeline import EvaluationProfile, RecordingGateway, evaluate_case
from ase.application.ports.llm import LlmGateway
from ase.domain.evaluations import (
    RESULT_NOTICE,
    CheckValue,
    EvaluationCaseInfo,
    EvaluationCaseSummary,
    EvaluationConnection,
    EvaluationRun,
    EvaluationRunStatus,
    EvaluationStopReason,
)

MAX_ARTEFACT_BYTES = 8 * 1024 * 1024
MIN_REDACTED_LENGTH = 6
RATIO_CHECKS = (
    "raw_citation_reference_validity",
    "final_citation_reference_validity",
    "required_evidence_selected_recall",
    "required_evidence_cited_recall",
    "counterevidence_selected_recall",
    "counterevidence_referenced_any_role_recall",
)
COUNT_CHECKS = (
    "raw_report_json_parse_failures",
    "uncited_statement_fields",
    "statement_fields",
    "validation_errors",
    "validation_warnings",
    "expected_declared_organisation_groups_match",
)


def _json_bytes(value: Any) -> bytes:
    def convert(item: Any) -> str:
        if isinstance(item, datetime):
            return item.isoformat()
        raise TypeError("The evaluation contains a value which cannot be serialised.")

    return (json.dumps(value, indent=2, ensure_ascii=False, default=convert) + "\n").encode()


def _tokens(calls: list[dict[str, Any]], key: str) -> int | None:
    counts = [call[key] for call in calls if isinstance(call.get(key), int)]
    return sum(counts) if counts else None


def summarise(result: Mapping[str, Any]) -> EvaluationCaseSummary:
    """Keep only bounded structural checks; prompts and answers stay in the artefact."""
    metrics = result["deterministic"]
    checks: dict[str, CheckValue] = {name: metrics[name]["value"] for name in RATIO_CHECKS}
    checks.update({name: metrics[name] for name in COUNT_CHECKS})
    calls = result["report"]["model_calls"]
    return EvaluationCaseSummary(
        case_id=result["case_id"],
        fingerprint=result["case_sha256"],
        report_status=result["report"]["status"],
        model_calls=len(calls),
        checks=checks,
        prompt_tokens=_tokens(calls, "prompt_tokens"),
        completion_tokens=_tokens(calls, "completion_tokens"),
    )


def _call_record(record: Mapping[str, Any], *, content: bool) -> dict[str, Any]:
    kept = {key: value for key, value in record.items() if key != "error"}
    if "error" in record:
        kept["error"] = "provider_error"
    if not content:
        kept.pop("messages", None)
        kept.pop("content", None)
        kept["content_omitted"] = "artefact size limit"
    return kept


class PackagedEvaluationSession:
    def __init__(
        self,
        run: EvaluationRun,
        connection: EvaluationConnection,
        cases: Mapping[str, EvaluationCase],
        gateway: LlmGateway,
        api_key: str,
        admit: Callable[[], Awaitable[None]],
    ) -> None:
        self._run, self._connection, self._cases = run, connection, cases
        self._api_key = api_key
        # The CLI's public profile shape; base URL and key stay out of every output.
        self._profile = EvaluationProfile(
            name=connection.name[:80],
            base_url=connection.base_url,
            model=connection.model,
            max_output_tokens=max(64, min(connection.max_output_tokens, 32000)),
            temperature=connection.temperature,
            reasoning_effort=connection.reasoning_effort,
        )
        self._recording = RecordingGateway(gateway, run.max_calls, admit)
        self._results: list[dict[str, Any]] = []
        self._active: str | None = None

    async def evaluate(self, case_id: str) -> EvaluationCaseSummary:
        self._active = case_id
        result = await evaluate_case(
            self._cases[case_id],
            self._profile,
            self._recording,
            self._api_key,
            provider=self._connection.provider,
        )
        self._results.append(result)
        self._active = None
        return summarise(result)

    def artefact(
        self,
        status: EvaluationRunStatus,
        reason: EvaluationStopReason | None,
        finished_at: datetime,
    ) -> bytes | None:
        for content in (True, False):
            archive = self._archive(status, reason, finished_at, content=content)
            if len(archive) <= MAX_ARTEFACT_BYTES:
                return archive
        return None

    def _results_document(
        self,
        status: EvaluationRunStatus,
        reason: EvaluationStopReason | None,
        finished_at: datetime,
        *,
        content: bool,
    ) -> dict[str, Any]:
        cases = []
        for result in self._results:
            report = dict(result["report"])
            report["model_calls"] = [
                _call_record(call, content=content) for call in report["model_calls"]
            ]
            cases.append({**result, "report": report})
        finished_calls = sum(len(result["report"]["model_calls"]) for result in self._results)
        connection = self._connection
        return {
            "run_id": str(self._run.id),
            "started_at": self._run.created_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            # The CLI vocabulary: only a completed run is a complete sample.
            "status": "completed" if status is EvaluationRunStatus.COMPLETED else "interrupted",
            "app_status": status.value,
            "stop_reason": reason.value if reason else None,
            "active_case": self._active,
            "connection": {
                "profile_id": str(connection.profile_id),
                "name": connection.name,
                "model": connection.model,
                "provider": connection.provider.value,
                "max_output_tokens": connection.max_output_tokens,
                "temperature": connection.temperature,
                "reasoning_effort": connection.reasoning_effort,
            },
            "selected_cases": list(self._run.case_ids),
            "max_calls": self._run.max_calls,
            "cases": cases,
            "model_calls": len(self._recording.records),
            "unfinished_case_calls": [
                _call_record(call, content=content)
                for call in self._recording.records[finished_calls:]
            ],
            "notice": RESULT_NOTICE,
        }

    def _archive(
        self,
        status: EvaluationRunStatus,
        reason: EvaluationStopReason | None,
        finished_at: datetime,
        *,
        content: bool,
    ) -> bytes:
        results = self._results_document(status, reason, finished_at, content=content)
        files = {
            "results.json": _json_bytes(results),
            "review.json": _json_bytes(review_template(results)),
        }
        for result in self._results:
            files[f"{result['case_id']}.md"] = result["report"]["markdown"].encode()
        buffer = io.BytesIO()
        stamp = finished_at.timetuple()[:6]
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, data in files.items():
                info = zipfile.ZipInfo(name, date_time=stamp)
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, self._redact(data))
        return buffer.getvalue()

    def _redact(self, data: bytes) -> bytes:
        """Defence in depth: by construction no file names the endpoint or its key."""
        for secret in (self._api_key, self._connection.base_url):
            if len(secret) >= MIN_REDACTED_LENGTH:
                data = data.replace(secret.encode(), b"[redacted]")
        return data


class PackagedEvaluationHarness:
    def __init__(self, casebooks: tuple[str, ...] = CASEBOOKS) -> None:
        self._casebooks = casebooks

    @cached_property
    def _loaded(self) -> tuple[tuple[str, EvaluationCase], ...]:
        return tuple(
            (casebook, case) for casebook in self._casebooks for case in packaged_cases(casebook)
        )

    def catalogue(self) -> tuple[EvaluationCaseInfo, ...]:
        return tuple(
            EvaluationCaseInfo(case.id, casebook, case.title, case.fingerprint)
            for casebook, case in self._loaded
        )

    def open(
        self,
        run: EvaluationRun,
        connection: EvaluationConnection,
        gateway: LlmGateway,
        api_key: str,
        admit: Callable[[], Awaitable[None]],
    ) -> PackagedEvaluationSession:
        cases = {case.id: case for _, case in self._loaded}
        return PackagedEvaluationSession(run, connection, cases, gateway, api_key, admit)
