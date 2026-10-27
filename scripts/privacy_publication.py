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
# Structured public documents. Strings are published wording; {"pending": ...} marks
# a decision the operator has not made and always blocks publication.
DOCUMENT_DATES = {
    "terms.json": ("version",),
    "acceptable-use.json": (),
    "accessibility.json": ("lastReviewed", "nextReview"),
}
SERVICE_FIELDS = ("businessDisclosure", "businessAddress", "accessibilityContact")
REQUIRED_FILES = {
    "privacy.json",
    "service.json",
    "storage.json",
    "attributions.generated.json",
    "approval.json",
    *DOCUMENT_DATES,
}
UNRESOLVED = re.compile(
    r"\b(TODO|TBC|TBD|placeholder|pending approval|awaiting confirmation|"
    r"not (?:yet )?(?:decided|confirmed|approved)|to be confirmed)\b",
    re.IGNORECASE,
)


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


def _iso_date(value: object) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _document_complete(
    document: object, dated: tuple[str, ...], valid: Callable[[object], bool]
) -> bool:
    """Every section needs an id, title and wording; any pending decision blocks it."""
    if not isinstance(document, dict) or not all(
        _iso_date(document.get(key)) for key in dated
    ):
        return False
    sections = document.get("sections")
    if not isinstance(sections, list) or not sections:
        return False
    for section in sections:
        if not isinstance(section, dict):
            return False
        paragraphs = section.get("paragraphs")
        items = section.get("items", [])
        if not (
            valid(section.get("id"))
            and valid(section.get("title"))
            and isinstance(paragraphs, list)
            and paragraphs
            and isinstance(items, list)
            and all(valid(value) for value in [*paragraphs, *items])
        ):
            return False
    return True


def validate_publication(files: dict[str, str]) -> None:
    """Errors name missing fields only, never values or candidate file contents."""
    if not REQUIRED_FILES <= files.keys():
        raise PublicationError(
            "Public policy publication blocked: required content missing."
        )
    try:

        def reject_constant(_value: str) -> None:
            # Match JSON.parse: Python otherwise accepts NaN and infinities.
            raise ValueError("Non-standard JSON constant")

        content = {
            name: json.loads(files[name], parse_constant=reject_constant)
            for name in REQUIRED_FILES
        }
        notice = content["privacy.json"]
        service = content["service.json"]
        approval = content["approval.json"]
        operator = notice["operator"]
        purposes = notice["purposes"]

        def valid(value: object) -> bool:
            return (
                isinstance(value, str)
                and len(value.strip()) >= 3
                and not UNRESOLVED.search(value)
            )

        if not all(valid(operator.get(key)) for key in REQUIRED_OPERATOR):
            raise PublicationError(
                "Public policy publication blocked: operator details incomplete."
            )
        if not all(valid(service.get(key)) for key in SERVICE_FIELDS):
            raise PublicationError(
                "Public policy publication blocked: service details incomplete."
            )
        for name, dated in DOCUMENT_DATES.items():
            if not _document_complete(content[name], dated, valid):
                raise PublicationError(
                    "Public policy publication blocked: public documents incomplete."
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
        if not _iso_date(approval["approvedOn"]):
            raise ValueError("Invalid approval date")
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
