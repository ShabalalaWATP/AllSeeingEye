"""Browser and PDF validation run inside the configured isolated resource boundary."""

import io
import json
import subprocess  # nosec B404
import sys
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import ArrayObject, BooleanObject, DictionaryObject

MAX_PDF_BYTES = 16 * 1024 * 1024
MAX_PAGES = 128


def _require_structure_entries(structure: DictionaryObject) -> None:
    children = structure.get("/K")
    children = children.get_object() if children is not None else None
    if isinstance(children, DictionaryObject):
        children = ArrayObject([children])
    if not isinstance(children, ArrayObject) or not children:
        raise ValueError("Empty tagged PDF structure")
    for reference in children:
        child = reference.get_object()
        if not isinstance(child, DictionaryObject) or child.get("/Type") != "/StructElem":
            raise ValueError("Invalid top-level PDF structure element")
    parent_tree = structure.get("/ParentTree")
    parent_tree = parent_tree.get_object() if parent_tree is not None else None
    if not isinstance(parent_tree, DictionaryObject):
        raise ValueError("Missing tagged PDF parent mapping")
    mappings = []
    for key in ("/Nums", "/Kids"):
        value = parent_tree.get(key)
        if value is not None:
            value = value.get_object()
            if not isinstance(value, ArrayObject) or not value:
                raise ValueError("Invalid tagged PDF parent mapping array")
            mappings.append(value)
    if not mappings:
        raise ValueError("Missing tagged PDF parent mapping")


def main() -> int:
    try:
        browser = sys.argv[1]
        command = [
            browser,
            "--headless",
            "--disable-background-networking",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-dev-shm-usage",
            "--user-data-dir=/work/profile",
            "--no-pdf-header-footer",
            "--export-tagged-pdf",
            "--virtual-time-budget=5000",
            "--print-to-pdf=/work/result.pdf",
            "file:///work/input.html",
        ]
        # The executable and fixed arguments are supplied only by trusted composition.
        subprocess.run(  # noqa: S603  # nosec B603
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=45,
        )  # nosec B603
        with Path("result.pdf").open("rb") as stream:
            data = stream.read(MAX_PDF_BYTES + 1)
        if len(data) > MAX_PDF_BYTES or not data.startswith(b"%PDF-"):
            raise ValueError("Invalid PDF output")
        pdf = PdfReader(io.BytesIO(data), strict=True)
        pages = len(pdf.pages)
        if not 1 <= pages <= MAX_PAGES or pdf.is_encrypted:
            raise ValueError("Invalid PDF page count")
        root = pdf.trailer["/Root"]
        if not isinstance(root, DictionaryObject):
            raise ValueError("Missing PDF root")
        marks = root.get("/MarkInfo")
        marks = marks.get_object() if marks is not None else None
        marked = marks.get("/Marked") if isinstance(marks, DictionaryObject) else None
        structure = root.get("/StructTreeRoot")
        structure = structure.get_object() if structure is not None else None
        if not isinstance(marked, BooleanObject) or marked.value is not True:
            raise ValueError("Missing tagged PDF marker")
        if (
            not isinstance(structure, DictionaryObject)
            or structure.get("/Type") != "/StructTreeRoot"
        ):
            raise ValueError("Missing tagged PDF structure")
        _require_structure_entries(structure)
        # Structural admission only, not PDF/UA or screen-reader acceptance.
        sys.stdout.buffer.write(json.dumps({"pages": pages, "bytes": len(data)}).encode() + b"\n")
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
        return 0
    except Exception:
        # Raw browser/parser details may contain private report text or local paths.
        return 1


if __name__ == "__main__":
    sys.exit(main())
