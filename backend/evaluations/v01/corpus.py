"""Load only bounded local files named and hashed by the frozen V01 manifest."""

import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from evaluations.v01.schema import ContractCase, Manifest

DEFAULT_ROOT = Path(__file__).parent
MAX_CASE_BYTES = 64 * 1024


@dataclass(frozen=True)
class Corpus:
    manifest: Manifest
    manifest_sha256: str
    cases: tuple[ContractCase, ...]


def _read_bounded(path: Path, root: Path) -> bytes:
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Evaluation path escapes its corpus root")
    if path.stat().st_size > MAX_CASE_BYTES:
        raise ValueError("Evaluation file exceeds its size bound")
    with path.open("rb") as handle:
        result = handle.read(MAX_CASE_BYTES + 1)
    if len(result) > MAX_CASE_BYTES:
        raise ValueError("Evaluation file exceeds its size bound")
    return result


def _validate_chains(cases: tuple[ContractCase, ...]) -> None:
    snapshots: dict[tuple[str, int], tuple[str, tuple[tuple[str, str], ...]]] = {}
    for case in cases:
        if case.edition is None:
            continue
        for snapshot in (case.edition.previous, case.edition.current):
            identities = tuple(
                sorted(
                    (item.id, item.model_dump_json())
                    for item in case.packet
                    if item.id in {record.packet_id for record in snapshot.evidence}
                )
            )
            key = case.edition.subscription_id, snapshot.number
            value = snapshot.model_dump_json(), identities
            if key in snapshots and snapshots[key] != value:
                raise ValueError("Consecutive cases disagree on their shared frozen edition")
            snapshots[key] = value


def load_corpus(root: Path = DEFAULT_ROOT) -> Corpus:
    manifest_bytes = _read_bounded(root / "manifest.json", root)
    manifest = Manifest.model_validate_json(manifest_bytes)
    ids = [entry.id for entry in manifest.cases]
    paths = [entry.path for entry in manifest.cases]
    if len(set(ids)) != 60 or len(set(paths)) != 60:
        raise ValueError("Manifest case identities and paths must be unique")
    if sorted(Counter(entry.domain for entry in manifest.cases).values()) != [10] * 6:
        raise ValueError("The manifest requires ten cases in each of six domains")
    for domain in {entry.domain for entry in manifest.cases}:
        counts = Counter(entry.split for entry in manifest.cases if entry.domain == domain)
        if counts != {"development": 8, "held_out": 2}:
            raise ValueError("Each domain requires eight development and two held-out cases")
    cases = []
    for entry in manifest.cases:
        content = _read_bounded(root / entry.path, root)
        if hashlib.sha256(content).hexdigest() != entry.sha256:
            raise ValueError(f"Frozen case digest mismatch: {entry.id}")
        case = ContractCase.model_validate_json(content)
        if (case.id, case.domain, case.split) != (entry.id, entry.domain, entry.split):
            raise ValueError("Case identity, domain or split differs from its manifest entry")
        cases.append(case)
    result = tuple(cases)
    if sum(case.edition is not None for case in result) < 12:
        raise ValueError("At least twelve cases must compare consecutive editions")
    _validate_chains(result)
    return Corpus(manifest, hashlib.sha256(manifest_bytes).hexdigest(), result)
