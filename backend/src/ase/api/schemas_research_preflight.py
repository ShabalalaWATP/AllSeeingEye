"""Exact-revision preview response; no request body can rewrite the saved brief."""

from pydantic import BaseModel

from ase.application.research.preflight import ResearchPreflight


class ResearchPreflightOut(BaseModel):
    preflight: ResearchPreflight
