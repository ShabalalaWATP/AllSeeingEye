"""PDF self-declared AI markers; browser parsing remains inside its isolated child."""

import io

from pypdf import PdfReader, PdfWriter

from ase.domain.ai_disclosure import AiDisclosure


def mark_pdf(content: bytes, disclosure: AiDisclosure | None) -> bytes:
    if disclosure is None:
        return content
    reader = PdfReader(io.BytesIO(content), strict=True)
    # Clone the complete document, preserving outlines, links, fonts and tagged structure.
    writer = PdfWriter(clone_from=reader)
    writer.add_metadata(
        {
            "/Keywords": "AI-generated, AI-assisted assessment"
            if disclosure.assessment_generated
            else "Application-written gap notice",
            **{f"/{key}": value for key, value in disclosure.metadata().items()},
        }
    )
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
