"""Run explicitly selected local-model evaluations or score an existing human review."""

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway
from evaluations.casebook import CASE_DIRECTORY, load_cases
from evaluations.human_review import human_metrics, review_template
from evaluations.pipeline import EvaluationProfile, RecordingGateway, evaluate_case


def json_bytes(value: Any) -> bytes:
    def convert(item: Any) -> str:
        if isinstance(item, datetime):
            return item.isoformat()
        raise TypeError("The evaluation contains a value which cannot be serialised.")

    return (json.dumps(value, indent=2, ensure_ascii=False, default=convert) + "\n").encode()


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Synthetic OSINT evaluation using the app Producer."
    )
    commands = command.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate fixtures without any model calls.")
    validate.add_argument("--cases-dir", type=Path, default=CASE_DIRECTORY)
    run = commands.add_parser(
        "run", help="Call an explicitly configured model and save review artefacts."
    )
    run.add_argument("--profile", type=Path, required=True, help="Public evaluation-profile JSON.")
    run.add_argument("--cases-dir", type=Path, default=CASE_DIRECTORY)
    run.add_argument(
        "--case", action="append", default=[], help="Case id; repeat to select several."
    )
    run.add_argument(
        "--out", type=Path, help="A new output directory; existing directories are refused."
    )
    run.add_argument(
        "--max-calls", type=int, default=16, help="Global model-call limit, including retries."
    )
    run.add_argument("--timeout-seconds", type=int, default=120)
    score = commands.add_parser(
        "score", help="Score human annotations separately from structural checks."
    )
    score.add_argument("--results", type=Path, required=True)
    score.add_argument("--review", type=Path, required=True)
    score.add_argument("--out", type=Path, required=True, help="New semantic-metrics JSON file.")
    return command


async def run_evaluation(args: argparse.Namespace) -> Path:
    if not 1 <= args.max_calls <= 1000 or not 1 <= args.timeout_seconds <= 600:
        raise ValueError("Call and timeout limits are out of range.")
    if args.profile.stat().st_size > 16_000:
        raise ValueError("Profile configuration is too large.")
    configuration = EvaluationProfile.model_validate_json(args.profile.read_bytes())
    cases = load_cases(args.cases_dir)
    requested = set(args.case)
    if requested - {case.id for case in cases}:
        raise ValueError("An unknown case id was requested.")
    cases = [case for case in cases if not requested or case.id in requested]
    if configuration.research_mode and any(case.replay is None for case in cases):
        raise ValueError("Research evaluation requires replay scenarios for every selected case.")
    run_id = str(uuid4())
    output = args.out or Path(__file__).parent / "runs" / run_id
    output.mkdir(parents=True, exist_ok=False)
    gateway = OpenAiCompatibleGateway(timeout_seconds=args.timeout_seconds)
    recording = RecordingGateway(gateway, args.max_calls)
    results: dict[str, Any] = {
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "configuration": configuration.model_dump(mode="json"),
        "max_calls": args.max_calls,
        "cases": [],
        "status": "running",
        "active_case": None,
        "notice": "Synthetic cases and assistant-authored rubrics, pending human validation. "
        "Structural metrics are not factual accuracy or doctrine certification. Human semantic "
        "metrics remain uncomputed until an attributed review is supplied.",
    }
    try:
        # This is the only secret setting read. No Settings, .env, database, saved
        # profile, feed collector or archiving path is opened by this harness.
        key = os.environ.get("ASE_EVAL_API_KEY", "")
        for case in cases:
            results["active_case"] = case.id
            result = await evaluate_case(case, configuration, recording, key)
            results["cases"].append(result)
            (output / f"{case.id}.md").write_bytes(result["report"]["markdown"].encode())
            results["model_calls"] = len(recording.records)
            (output / "results.json").write_bytes(json_bytes(results))
        (output / "review.json").write_bytes(json_bytes(review_template(results)))
        results["status"] = "completed"
        results["active_case"] = None
    finally:
        # Preserve failed-case calls too, without persisting arbitrary exception
        # messages. An interrupted run must never look like a completed sample.
        if results["status"] == "running":
            results["status"] = "interrupted"
        results["model_calls"] = len(recording.records)
        results["model_call_records"] = recording.records
        results["finished_at"] = datetime.now(UTC).isoformat()
        try:
            (output / "results.json").write_bytes(json_bytes(results))
        finally:
            await gateway.aclose()
    return output


def main(argv: list[str] | None = None) -> int:
    command = parser()
    args = command.parse_args(argv)
    try:
        if args.command == "validate":
            cases = load_cases(args.cases_dir)
            print(f"Validated {len(cases)} synthetic cases. Human reference review is pending.")  # noqa: T201
        elif args.command == "run":
            output = asyncio.run(run_evaluation(args))
            print(f"Saved model outputs and an unlabelled human review to {output}")  # noqa: T201
        else:
            if args.results.stat().st_size > 128_000_000 or args.review.stat().st_size > 8_000_000:
                raise ValueError("Evaluation artefacts exceed the supported size.")
            results = json.loads(args.results.read_bytes())
            review = json.loads(args.review.read_bytes())
            metrics = human_metrics(results, review)
            with args.out.open("xb") as target:
                target.write(json_bytes(metrics))
            print(f"Saved attributed semantic review metrics to {args.out}")  # noqa: T201
    except (ValueError, OSError, KeyError, TypeError) as exc:
        # Pydantic and filesystem exceptions can contain input values. Do not echo
        # profile contents, model credentials or arbitrary paths on failure.
        command.exit(2, f"Evaluation input or output failed validation ({type(exc).__name__}).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
