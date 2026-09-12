"""The Markdown endpoint chooses a portable figure package at release time."""

import io
import zipfile
from dataclasses import replace

from httpx import AsyncClient
from PIL import Image

from ase.api.routers import reports as reports_router
from ase.container import Container
from ase.domain.report_documents import BlockKind, DocumentBlock, DocumentFigure
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_documents_helpers import document_records


async def test_markdown_endpoint_returns_named_zip_when_publication_has_a_figure(
    client: AsyncClient,
    container: Container,
    user: User,
    monkeypatch,
) -> None:
    record, version = document_records(user.id)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    original_build = reports_router.build_document
    image = io.BytesIO()
    Image.new("RGB", (8, 8), "black").save(image, format="PNG")
    figure = DocumentFigure(
        "Location plot",
        "Locations retained in the report.",
        "Location plot",
        image.getvalue(),
        "image/png",
        8,
        8,
    )

    def build_with_figure(found_record, found_version):
        document = original_build(found_record, found_version)
        return replace(
            document,
            blocks=(
                *document.blocks,
                DocumentBlock(BlockKind.FIGURE, figure.caption, figure=figure),
            ),
        )

    monkeypatch.setattr(reports_router, "build_document", build_with_figure)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = {**bearer(token), "Accept": "application/zip"}
    response = await client.get(f"/api/reports/{record.id}/markdown", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="report-{record.id}-v1-markdown.zip"'
    )
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        markdown = archive.read("report.md").decode()
        assert "![Location plot](figures/figure-1.png)" in markdown
        assert archive.read("figures/figure-1.png").startswith(b"\x89PNG")


async def test_markdown_endpoint_preserves_explicit_text_contract(
    client: AsyncClient,
    container: Container,
    user: User,
    monkeypatch,
) -> None:
    record, version = document_records(user.id)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    original_build = reports_router.build_document
    image = io.BytesIO()
    Image.new("RGB", (8, 8), "black").save(image, format="PNG")
    figure = DocumentFigure(
        "Location plot",
        "Locations retained in the report.",
        "Location plot",
        image.getvalue(),
        "image/png",
        8,
        8,
    )

    def build_with_figure(found_record, found_version):
        document = original_build(found_record, found_version)
        return replace(
            document,
            blocks=(
                *document.blocks,
                DocumentBlock(BlockKind.FIGURE, figure.caption, figure=figure),
            ),
        )

    monkeypatch.setattr(reports_router, "build_document", build_with_figure)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = {**bearer(token), "Accept": "text/markdown"}
    response = await client.get(f"/api/reports/{record.id}/markdown", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="report-{record.id}-v1.md"'
    )
    assert "Location plot" in response.text
    assert "figures/figure-1.png" not in response.text


async def test_markdown_endpoint_rejects_zero_quality_and_similar_zip_types(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    record, version = document_records(user.id)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    for accept in (
        "text/markdown, application/zip;q=0",
        "application/zipper",
        "text/markdown;q=1, application/zip;q=0.1",
    ):
        headers = {**bearer(token), "Accept": accept}
        response = await client.get(f"/api/reports/{record.id}/markdown", headers=headers)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/markdown; charset=utf-8"
