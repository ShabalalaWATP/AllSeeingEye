"""Pure opt-in exact-subject capability for existing one-request registry adapters."""

from ase.domain.registry_identifiers import registry_subject


class RegistryLookupCapability:
    registry_namespaces: tuple[str, ...] = ()

    def registry_subject(self, namespace: str, value: str) -> str | None:
        if namespace not in self.registry_namespaces:
            return None
        return registry_subject(namespace, value)
