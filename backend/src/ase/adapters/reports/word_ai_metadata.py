"""Typed OOXML AI properties; no signature or content-authenticity claim."""

# Construct fixed OOXML only. No XML parser or untrusted XML input is used here.
from xml.etree.ElementTree import Element, SubElement, tostring  # nosec B405

from docx.document import Document
from docx.opc.constants import CONTENT_TYPE, RELATIONSHIP_TYPE
from docx.opc.packuri import PackURI
from docx.opc.part import Part

from ase.domain.report_documents import ReportDocument

CUSTOM_NS = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
VALUE_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"


def set_docx_metadata(word: Document, document: ReportDocument) -> None:
    word.core_properties.title = document.title
    word.core_properties.author = "The All Seeing Eye"
    word.core_properties.subject = document.reference
    word.core_properties.comments = ""
    disclosure = document.ai_disclosure
    if disclosure is None:
        return
    word.core_properties.keywords = (
        "AI-generated, AI-assisted assessment"
        if disclosure.assessment_generated
        else "Application-written gap notice"
    )
    word.core_properties.comments = disclosure.statement[:255]
    properties = Element(f"{{{CUSTOM_NS}}}Properties")
    for identifier, (name, value) in enumerate(disclosure.metadata().items(), start=2):
        prop = SubElement(
            properties,
            f"{{{CUSTOM_NS}}}property",
            fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}",
            pid=str(identifier),
            name=name,
        )
        kind = "bool" if name == "ase:ai-generated" else "lpwstr"
        SubElement(prop, f"{{{VALUE_NS}}}{kind}").text = value
    package = word.part.package
    part = Part(
        PackURI("/docProps/custom.xml"),
        CONTENT_TYPE.OFC_CUSTOM_PROPERTIES,
        tostring(properties, encoding="utf-8", xml_declaration=True),
        package,
    )
    package.relate_to(part, RELATIONSHIP_TYPE.CUSTOM_PROPERTIES)
