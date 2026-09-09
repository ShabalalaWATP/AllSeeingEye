"""Bounded explicit waypoint inputs and transient route output."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, TypeAdapter, ValidationError

from ase.domain.navigation import RouteMode


class NavigationPointIn(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class NavigationRouteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: RouteMode
    waypoints: list[NavigationPointIn] = Field(min_length=2, max_length=8)


class NavigationStepOut(BaseModel):
    instruction: str = Field(max_length=500)
    distance_km: float = Field(ge=0, le=5000)
    duration_seconds: float = Field(ge=0, le=604800)


class NavigationCapabilitiesOut(BaseModel):
    provider: str = "FOSSGIS Valhalla"
    operator_contact: str
    available: bool
    configuration_message: str | None = None
    privacy: str = (
        "Calculate route sends the entered coordinates to FOSSGIS, which may log requests."
    )


def navigation_capabilities(contact: str) -> NavigationCapabilitiesOut:
    try:
        address = str(TypeAdapter(EmailStr).validate_python(contact))
        domain = address.rsplit("@", 1)[1].lower()
        valid = not any(
            domain == suffix or domain.endswith("." + suffix)
            for suffix in ("invalid", "test", "localhost", "local")
        )
    except ValidationError:
        address, valid = "", False
    return NavigationCapabilitiesOut(
        operator_contact=address if valid else "",
        available=valid,
        configuration_message=None
        if valid
        else (
            "Routing needs a valid public operator email in ASE_FEEDS_CONTACT. "
            "Ask the administrator to configure it before calculating routes."
        ),
    )


class NavigationRouteOut(BaseModel):
    mode: RouteMode
    distance_km: float = Field(ge=0, le=5000)
    duration_seconds: float = Field(ge=0, le=604800)
    coordinates: list[
        tuple[Annotated[float, Field(ge=-180, le=180)], Annotated[float, Field(ge=-90, le=90)]]
    ] = Field(min_length=2, max_length=20000)
    steps: list[NavigationStepOut] = Field(min_length=1, max_length=500)
    provider: Literal["FOSSGIS Valhalla"] = "FOSSGIS Valhalla"
    attribution: str = "Data © OpenStreetMap contributors (ODbL). Routing: FOSSGIS Valhalla."
    limitations: str = (
        "Planning estimate only. Road access, closures, conditions and travel times may be wrong. "
        "Verify locally before travelling."
    )
