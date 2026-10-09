"""Root-owned publication policy. Parse candidate Git blobs; never execute them."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from datetime import date

POLICY_PATH = "frontend/src/features/public-policy/"
REQUIRED_OPERATOR = (
    "controllerName",
    "controllerContact",
    "complaintsContact",
    "complaintsProcedure",
    "jurisdiction",
    "hosting",
    "emailProvider",
    "aiProviders",
    "otherRecipients",
    "internationalTransfers",
    "retentionCriteria",
    "publicSourceAssessment",
    "storageAssessment",
    "automatedDecisions",
)
REQUIRED_FILES = {
    "privacy.json",
    "storage.json",
    "attributions.generated.json",
    "approval.json",
}


class PublicationError(RuntimeError):
    """Candidate public policy is incomplete or its wording lacks matching approval."""


def policy_hash(files: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for name, content in sorted(files.items()):
        if (
            name != "approval.json"
            and re.search(r"\.(json|tsx?|css)$", name)
            and ".test." not in name
        ):
            digest.update(name.encode())
            digest.update(b"\0")
            digest.update(content.replace("\r\n", "\n").strip().encode())
            digest.update(b"\0")
    return digest.hexdigest()


def validate_publication(files: dict[str, str]) -> None:
    """Errors name missing fields only, never values or candidate file contents."""
    if not REQUIRED_FILES <= files.keys():
        raise PublicationError(
            "Public policy publication blocked: required content missing."
        )
    try:
        notice = json.loads(files["privacy.json"])
        approval = json.loads(files["approval.json"])
        operator = notice["operator"]
        purposes = notice["purposes"]

        def valid(value: object) -> bool:
            return (
                isinstance(value, str)
                and len(value.strip()) >= 3
                and not re.search(
                    r"\b(TODO|TBC|TBD|placeholder|pending approval|awaiting confirmation)\b",
                    value,
                    re.IGNORECASE,
                )
            )

        if not all(valid(operator.get(key)) for key in REQUIRED_OPERATOR):
            raise PublicationError(
                "Public policy publication blocked: operator details incomplete."
            )
        if (
            not isinstance(purposes, list)
            or len(purposes) < 5
            or not all(valid(purpose.get("lawfulBasis")) for purpose in purposes)
        ):
            raise PublicationError(
                "Public policy publication blocked: lawful bases incomplete."
            )
        if not valid(approval.get("approvedBy")):
            raise PublicationError(
                "Public policy publication blocked: approval missing."
            )
        approved_on = approval["approvedOn"]
        if not isinstance(approved_on, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", approved_on
        ):
            raise ValueError("Invalid approval date")
        date.fromisoformat(approved_on)
        if approval.get("contentSha256") != policy_hash(files):
            raise PublicationError(
                "Public policy publication blocked: content changed or unapproved."
            )
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise PublicationError(
            "Public policy publication blocked: invalid content or approval."
        ) from exc


def require_publication(sha: str, git: Callable[..., str]) -> None:
    """Read the exact candidate revision before backup, image inspection or cutover."""
    files = {}
    listing = git("ls-tree", "-r", sha, "--", POLICY_PATH)
    for row in listing.splitlines():
        metadata, separator, path = row.partition("\t")
        name = path.removeprefix(POLICY_PATH)
        if not separator or not path.startswith(POLICY_PATH) or "/" in name:
            raise PublicationError(
                "Public policy publication blocked: unexpected content path."
            )
        if metadata.split()[:2] != ["100644", "blob"]:
            raise PublicationError(
                "Public policy publication blocked: content must be regular files."
            )
        files[name] = git("show", f"{sha}:{path}")
    validate_publication(files)
