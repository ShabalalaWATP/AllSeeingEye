"""Reference notes: a packaged catalogue loaded once per process, no per-request network."""

from functools import cached_property

from ase.adapters.reference import load_reference
from ase.domain.reference import ReferenceCatalogue


class ReferenceWiring:
    @cached_property
    def reference_catalogue(self) -> ReferenceCatalogue:
        return load_reference()
