"""Regenerate the packaged actor projection from an explicitly downloaded STIX file.

Run from backend with its existing uv environment:
    uv run python ../scripts/import_cyber_actors.py SOURCE.json --commit COMMIT \
        --retrieved-at 2026-09-12T22:08:00+00:00

Download the chosen release and LICENSE.txt from the same full upstream commit at
https://github.com/mitre-attack/attack-stix-data. Review source changes and preserve
the upstream licence in cyber_reference/LICENSE.txt before committing the result.
The importer performs no network requests and follows no links in supplied STIX.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ase.adapters.cyber_reference.catalogue import utc_date
from ase.adapters.cyber_reference.projection import MAX_STIX_BYTES, project_actor_catalogue

OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "backend/src/ase/adapters/cyber_reference/enterprise_actors.json"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--commit", required=True, help="Full upstream Git commit hash")
    parser.add_argument("--retrieved-at", required=True, help="Timezone-aware retrieval timestamp")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    with args.source.open("rb") as source:
        payload = source.read(MAX_STIX_BYTES + 1)
    result = project_actor_catalogue(
        payload, commit=args.commit, retrieved_at=utc_date(args.retrieved_at)
    )
    args.output.write_bytes(result)


if __name__ == "__main__":
    main()
