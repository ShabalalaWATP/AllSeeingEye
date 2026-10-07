"""The signed-out site facts: public, minimal and off unless the operator opts in."""

from __future__ import annotations

from httpx import AsyncClient

from ase.container import Container


async def test_product_page_is_off_by_default(client: AsyncClient) -> None:
    response = await client.get("/api/site")
    assert response.status_code == 200
    assert response.json() == {"product_page_enabled": False}


async def test_product_page_follows_the_operator_setting(
    client: AsyncClient, container: Container
) -> None:
    container.settings = container.settings.model_copy(update={"public_product_page_enabled": True})
    response = await client.get("/api/site")
    assert response.json() == {"product_page_enabled": True}


async def test_site_facts_need_no_session_and_reveal_only_the_flag(client: AsyncClient) -> None:
    client.cookies.clear()
    response = await client.get("/api/site")
    assert response.status_code == 200
    assert set(response.json()) == {"product_page_enabled"}
    assert response.headers["cache-control"] == "no-store"
