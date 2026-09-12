"""Packaged MITRE ATT&CK reference metadata, with no runtime network access."""

from ase.adapters.cyber_reference.catalogue import load_actor_catalogue
from ase.adapters.cyber_reference.source import MITRE_ATTACK_SPEC

__all__ = ["MITRE_ATTACK_SPEC", "load_actor_catalogue"]
