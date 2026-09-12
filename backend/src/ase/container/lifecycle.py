"""Dispose composition-root resources in dependency order after workers stop."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ase.container import Container


async def dispose_resources(container: "Container") -> None:
    await container.close_economy()
    await container.http.aclose()
    await container.satellite_http.aclose()
    await container.marine_http.aclose()
    await container.barentswatch_http.aclose()
    await container.camera_http.aclose()
    await container.public_firms_http.aclose()
    await container.routing_http.aclose()
    await container.terrain_gateway.aclose()
    await container.terrain_http.aclose()
    await container._llm_gateway.aclose()
    await container.close_web_search()
    await container._embedding_gateway.aclose()
    await container.tiles.aclose()
    await container.archiver.aclose()
    await container.engine.dispose()
