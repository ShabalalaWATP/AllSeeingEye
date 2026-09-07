"""Frozen original fixtures with bytes distinct from extracted text and previews."""

import hashlib
from dataclasses import replace

from ase.domain.evidence_attributes import EvidenceAttribute
from report_documents_helpers import document_records

ORIGINAL = b"An original document, deliberately retained.\n"


async def original_report(container, user, team_id=None, content=ORIGINAL):
    record, version = document_records(user.id)
    record.team_id = team_id
    item = replace(
        version.evidence[0],
        source_id="research_import",
        url=None,
        attributes=tuple(
            EvidenceAttribute(key, value)
            for key, value in {
                "original_sha256": hashlib.sha256(content).hexdigest(),
                "filename": "source.txt",
                "media_type": "text/plain",
                "source_reference": "line 1",
                "sample_sha256": "b" * 64,
            }.items()
        ),
    )
    version = replace(version, evidence=(item, *version.evidence[1:]))
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    return record, version


def reserve_body(**changes):
    return {
        "version_number": 1,
        "evidence_label": "E1",
        "filename": "renamed.txt",
        "media_type": "text/plain",
        "permitted_use": "I own this document and permit retention.",
        "byte_count": len(ORIGINAL),
        "retention_days": 30,
        **changes,
    }


def asset_path(record):
    return f"/api/reports/{record.id}/original-assets"


async def retained(client, record, headers):
    response = await client.post(asset_path(record), headers=headers, json=reserve_body())
    assert response.status_code == 201, response.text
    asset = response.json()
    response = await client.put(
        f"{asset_path(record)}/{asset['id']}/content",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=ORIGINAL,
    )
    assert response.status_code == 200, response.text
    return response.json()
