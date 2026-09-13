"""Every offered workspace theme is a closed, validated vocabulary."""

import pytest

from ase.domain.profile import APPEARANCE_THEMES, PersonalProfile
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


def test_theme_vocabulary_is_closed_and_defaults_to_obsidian():
    assert APPEARANCE_THEMES == (
        "obsidian",
        "slate",
        "light",
        "midnight",
        "aurora",
        "phosphor",
        "crimson",
        "graphite",
    )
    assert PersonalProfile("Analyst").appearance_theme == "obsidian"
    with pytest.raises(ValueError):
        PersonalProfile("Analyst", appearance_theme="neon")  # type: ignore[arg-type]


@pytest.mark.parametrize("theme", APPEARANCE_THEMES)
async def test_each_theme_round_trips_through_the_profile_api(client, user, theme):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    response = await client.patch(
        "/api/me/profile", headers=headers, json={"appearance_theme": theme}
    )
    assert response.status_code == 200, response.text
    assert response.json()["appearance_theme"] == theme
    assert (await client.get("/api/me/profile", headers=headers)).json()[
        "appearance_theme"
    ] == theme
