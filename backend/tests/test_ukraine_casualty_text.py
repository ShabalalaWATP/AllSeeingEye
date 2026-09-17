"""Visible-text extraction regressions for the casualty importer."""

from datetime import date

import pytest

from ase.adapters.geo import ukraine_casualties_import as casualties


@pytest.mark.parametrize("tag", ["SCRIPT", "StYlE", "script", "style"])
@pytest.mark.parametrize("closing_slash", ["", "/"])
def test_hrmmu_ignores_hidden_script_and_style_casualty_text(tag: str, closing_slash: str) -> None:
    hidden = "At least 999 civilians were killed and 999 injured in Ukraine in July 2026."
    visible = "At least 12 civilians were killed and 34 injured in Ukraine in July 2026."
    result = casualties.parse_month(
        f'<{tag} data-test=">"{closing_slash}>{hidden}</{tag}><p>{visible}</p>',
        date(2026, 7, 1),
        "https://example.test/july",
    )
    assert result["killed"] == 12 and result["injured"] == 34


@pytest.mark.parametrize("outer,inner", [("script", "style"), ("style", "script")])
def test_hrmmu_self_closing_raw_text_keeps_nested_tag_text_inert(outer: str, inner: str) -> None:
    markup = f'<{outer}/>var x="<{inner}>";</{outer}><p>Visible content</p>'
    assert casualties._plain(markup) == "Visible content"
