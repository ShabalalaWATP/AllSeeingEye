"""Dispose composition-root resources in dependency order after workers stop."""

from contextlib import AsyncExitStack
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ase.container import Container


async def dispose_resources(container: "Container") -> None:
    async with AsyncExitStack() as cleanup:
        # Registration is reversed: dependants close before their clients and DB.
        # A failing callback cannot skip later callbacks; exceptions remain chained.
        cleanup.push_async_callback(container.engine.dispose)
        cleanup.push_async_callback(container.archiver.aclose)
        cleanup.push_async_callback(container.tiles.aclose)
        cleanup.push_async_callback(container._embedding_gateway.aclose)
        cleanup.push_async_callback(container.close_web_search)
        cleanup.push_async_callback(container._llm_gateway.aclose)
        cleanup.push_async_callback(container.terrain_http.aclose)
        cleanup.push_async_callback(container.terrain_gateway.aclose)
        cleanup.push_async_callback(container.routing_http.aclose)
        cleanup.push_async_callback(container.public_firms_http.aclose)
        cleanup.push_async_callback(container.camera_http.aclose)
        if container.acled_tokens is not None:
            cleanup.push_async_callback(container.acled_tokens.aclose)
        cleanup.push_async_callback(container.barentswatch_http.aclose)
        cleanup.push_async_callback(container.marine_http.aclose)
        cleanup.push_async_callback(container.satellite_http.aclose)
        cleanup.push_async_callback(container.http.aclose)
        cleanup.push_async_callback(container.close_economy)
        # Only stop the digest generator when something has actually built it.
        digest = container.__dict__.get("ukraine_digest")
        if digest is not None:
            cleanup.push_async_callback(digest.drain)
            cleanup.callback(digest.cancel)
