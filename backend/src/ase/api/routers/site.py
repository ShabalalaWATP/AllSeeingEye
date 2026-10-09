"""Public facts the signed-out pages need about this installation.

Deliberately unauthenticated: a new field here is public to anyone and
needs a security review. Not cached, so an operator's change takes effect at once.
"""

from __future__ import annotations

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep
from ase.api.schemas import PublicSiteOut

router = APIRouter(tags=["site"])


@router.get("/site")
async def site(container: ContainerDep, response: Response) -> PublicSiteOut:
    response.headers["Cache-Control"] = "no-store"
    return PublicSiteOut(
        product_page_enabled=container.settings.public_product_page_enabled,
        enterprise_enquiries_enabled=container.settings.enterprise_enquiries_enabled,
        enterprise_enquiry_retention_days=container.settings.enterprise_enquiry_retention_days,
    )
