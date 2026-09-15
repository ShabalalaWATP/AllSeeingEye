"""Offline V01 CLI. No settings, credentials, provider or model adapters are loaded."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import cast

from evaluations.v01.corpus import DEFAULT_ROOT, load_corpus
from evaluations.v01.reporting import evaluate
from evaluations.v01.schema import Split


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "contracts"))
    parser.add_argument("--corpus", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--split", choices=("all", "development", "held_out"), default="all")
    parser.add_argument("--out", type=Path, help="Create a new local JSON file; never overwrite.")
    args = parser.parse_args(argv)
    corpus = load_corpus(args.corpus)
    if args.command == "validate":
        result = {
            "manifest_sha256": corpus.manifest_sha256,
            "cases": len(corpus.cases),
            "domains": dict(Counter(case.domain for case in corpus.cases)),
            "splits": dict(Counter(case.split for case in corpus.cases)),
            "consecutive_edition_cases": sum(case.edition is not None for case in corpus.cases),
            "evidence_origin": "synthetic_assistant_authored",
            "human_review_status": "pending",
        }
    else:
        result = evaluate(corpus, None if args.split == "all" else cast(Split, args.split))
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8") as handle:
            handle.write(encoded)
    else:
        sys.stdout.write(encoded)
    return int(args.command == "contracts" and result["passed_case_count"] != result["case_count"])


if __name__ == "__main__":
    raise SystemExit(main())
