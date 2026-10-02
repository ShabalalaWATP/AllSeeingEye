"""Explicit STIX 2.1 built-in TLP markings, chosen for each export."""

from enum import StrEnum


class StixTlp(StrEnum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"
