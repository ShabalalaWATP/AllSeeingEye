"""Escape plain titles and links into Atom; never render report prose or HTML.

Construction/serialisation only. No untrusted XML is parsed by this module.
"""

import re
from typing import cast
from xml.etree.ElementTree import Element, SubElement, tostring  # nosec B405

from ase.domain.notification_feed import PrivateFeed


def render_atom(feed: PrivateFeed, base_url: str) -> bytes:
    root = Element("feed", xmlns="http://www.w3.org/2005/Atom")
    SubElement(root, "id").text = f"urn:ase:private-feed:{feed.user_id}"
    SubElement(root, "title").text = "The All Seeing Eye notifications"
    SubElement(SubElement(root, "author"), "name").text = "The All Seeing Eye"
    SubElement(root, "updated").text = feed.generated_at.isoformat()
    SubElement(root, "subtitle").text = (
        "Latest 100 accessible notifications; older entries are omitted."
        if feed.truncated
        else "Current accessible alerts and subscription editions."
    )
    for row in feed.entries:
        entry = SubElement(root, "entry")
        SubElement(entry, "id").text = f"urn:ase:{row.kind}:{row.id}"
        SubElement(entry, "title", type="text").text = re.sub(
            r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", "", row.title
        )
        SubElement(entry, "updated").text = row.updated_at.isoformat()
        SubElement(entry, "link", href=base_url.rstrip("/") + row.path)
    return cast(bytes, tostring(root, encoding="utf-8", xml_declaration=True))
