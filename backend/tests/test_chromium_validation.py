"""Pinned assets, bounded PDF validation and job-control path invariants."""

import asyncio
import io
from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    DictionaryObject,
    NameObject,
    NullObject,
    NumberObject,
    TextStringObject,
)

from ase.adapters.reports import chromium, chromium_pdf_child, print_html, render_cgroup
from ase.adapters.reports.chromium import ChromiumPdfWorker
from ase.adapters.reports.print_html import render_print_html
from ase.adapters.reports.render_cgroup import RenderCgroup
from ase.container.report_renderer import build_report_renderer
from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import BlockKind, DocumentBlock, ReportDocument


@pytest.mark.parametrize(
    "tagged,pages,accepted", [(True, 1, True), (False, 1, False), (True, 129, False)]
)
def test_child_validates_real_pdf_pages_and_tags(tmp_path, monkeypatch, tagged, pages, accepted):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(chromium_pdf_child.sys, "argv", ["worker", "/fixed/browser"])
    commands = []
    output = io.BytesIO()
    monkeypatch.setattr(chromium_pdf_child.sys, "stdout", SimpleNamespace(buffer=output))

    def browser(command, **kwargs):
        commands.append(command)
        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(200, 200)
        if tagged:
            writer.root_object.update(
                {
                    NameObject("/MarkInfo"): DictionaryObject(
                        {NameObject("/Marked"): BooleanObject(True)}
                    ),
                    NameObject("/StructTreeRoot"): DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/StructTreeRoot"),
                            NameObject("/K"): ArrayObject(
                                [DictionaryObject({NameObject("/Type"): NameObject("/StructElem")})]
                            ),
                            NameObject("/ParentTree"): DictionaryObject(
                                {
                                    NameObject("/Nums"): ArrayObject(
                                        [NumberObject(0), ArrayObject([NumberObject(0)])]
                                    )
                                }
                            ),
                        }
                    ),
                }
            )
        with Path("result.pdf").open("wb") as stream:
            writer.write(stream)

    monkeypatch.setattr(chromium_pdf_child.subprocess, "run", browser)
    assert (chromium_pdf_child.main() == 0) is accepted
    assert "--no-sandbox" not in commands[0]
    assert commands[0][-1] == "file:///work/input.html"
    assert bool(output.getvalue()) is accepted


def test_print_html_embeds_verified_fonts_and_escapes_markup(monkeypatch):
    document = ReportDocument(
        "title", "reference", (DocumentBlock(BlockKind.TEXT, "<script>private</script>"),), "fa"
    )
    html = render_print_html(document).decode()
    assert html.count("@font-face") == 2
    assert "font-src data:" in html and "&lt;script&gt;private&lt;/script&gt;" in html
    assert "<script>" not in html
    monkeypatch.setattr(print_html, "FONTS", (("Regular", 400, "0" * 64),))
    with pytest.raises(InvalidRequest, match="verified report font"):
        render_print_html(document)


async def test_renderer_output_byte_limit_is_checked_independently(monkeypatch):
    stream = asyncio.StreamReader()
    stream.feed_data(b'{"pages":1,"bytes":18}\n%PDF-1.7 too large')
    stream.feed_eof()
    monkeypatch.setattr(chromium, "MAX_PDF_BYTES", 10)
    with pytest.raises(ValueError):
        await ChromiumPdfWorker._result(stream)


def test_control_paths_cannot_escape_owned_job(tmp_path, monkeypatch):
    monkeypatch.setattr(render_cgroup, "owned_directory", lambda path: path.resolve(strict=True))
    parent = tmp_path / "delegated"
    parent.mkdir()
    child = parent / "ase-render-fixture"
    child.mkdir()
    (child / "cgroup.kill").write_text("")
    job = RenderCgroup(parent, child)
    assert job.control("cgroup.kill") == child / "cgroup.kill"
    with pytest.raises(InvalidRequest):
        job.control("../cgroup.kill")
    with pytest.raises(InvalidRequest):
        RenderCgroup(tmp_path, child).control("cgroup.kill")
    with pytest.raises(InvalidRequest):
        RenderCgroup(parent, parent).control("cgroup.kill")


def test_default_composition_has_no_browser_and_invalid_configuration_fails(tmp_path):
    assert build_report_renderer(None).worker is None
    with pytest.raises(InvalidRequest):
        build_report_renderer("relative/runtime.json")
    file = tmp_path / "runtime.json"
    file.write_text('{"enabled":true}')
    with pytest.raises(InvalidRequest):
        build_report_renderer(str(file))


@pytest.mark.parametrize("fault", ["false", "null", "wrong_type", "empty"])
def test_child_rejects_false_marker_and_invalid_structure(tmp_path, monkeypatch, fault):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(chromium_pdf_child.sys, "argv", ["worker", "/fixed/browser"])

    def browser(*args, **kwargs):
        writer = PdfWriter()
        writer.add_blank_page(200, 200)
        structure = DictionaryObject({NameObject("/Type"): NameObject("/StructTreeRoot")})
        if fault == "null":
            structure = NullObject()
        elif fault == "wrong_type":
            structure = NameObject("/StructTreeRoot")
        writer.root_object.update(
            {
                NameObject("/MarkInfo"): DictionaryObject(
                    {NameObject("/Marked"): BooleanObject(fault != "false")}
                ),
                NameObject("/StructTreeRoot"): structure,
            }
        )
        with Path("result.pdf").open("wb") as stream:
            writer.write(stream)

    monkeypatch.setattr(chromium_pdf_child.subprocess, "run", browser)
    assert chromium_pdf_child.main() == 1


@pytest.mark.parametrize(
    "variant,accepted",
    [
        ("nums_string", False),
        ("kids_string", False),
        ("nums_empty", False),
        ("kids_empty", False),
        ("child_null", False),
        ("child_number", False),
        ("child_wrong_dict", False),
        ("nums_valid", True),
        ("kids_valid", True),
    ],
)
def test_child_requires_typed_structure_entries(tmp_path, monkeypatch, variant, accepted):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(chromium_pdf_child.sys, "argv", ["worker", "/fixed/browser"])
    output = io.BytesIO()
    monkeypatch.setattr(chromium_pdf_child.sys, "stdout", SimpleNamespace(buffer=output))

    def browser(*args, **kwargs):
        writer = PdfWriter()
        writer.add_blank_page(200, 200)
        child = DictionaryObject({NameObject("/Type"): NameObject("/StructElem")})
        if variant == "child_null":
            child = NullObject()
        elif variant == "child_number":
            child = NumberObject(1)
        elif variant == "child_wrong_dict":
            child = DictionaryObject({NameObject("/Type"): NameObject("/Catalog")})
        mapping_key = "/Kids" if variant.startswith("kids") else "/Nums"
        mapping = ArrayObject([NumberObject(0), ArrayObject([NumberObject(0)])])
        if mapping_key == "/Kids":
            mapping = ArrayObject(
                [
                    writer._add_object(
                        DictionaryObject(
                            {
                                NameObject("/Nums"): mapping,
                            }
                        )
                    )
                ]
            )
        if variant.endswith("string"):
            mapping = TextStringObject("invalid-string")
        elif variant.endswith("empty"):
            mapping = ArrayObject()
        writer.root_object.update(
            {
                NameObject("/MarkInfo"): DictionaryObject(
                    {NameObject("/Marked"): BooleanObject(True)}
                ),
                NameObject("/StructTreeRoot"): DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/StructTreeRoot"),
                        NameObject("/K"): ArrayObject([writer._add_object(child)]),
                        NameObject("/ParentTree"): DictionaryObject(
                            {NameObject(mapping_key): mapping}
                        ),
                    }
                ),
            }
        )
        with Path("result.pdf").open("wb") as stream:
            writer.write(stream)

    monkeypatch.setattr(chromium_pdf_child.subprocess, "run", browser)
    assert (chromium_pdf_child.main() == 0) is accepted
    assert bool(output.getvalue()) is accepted
