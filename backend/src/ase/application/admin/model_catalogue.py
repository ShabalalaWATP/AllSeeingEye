"""Complete bounded model-ID catalogues, never silently truncated lists."""

from ase.domain.errors import InvalidRequest

MAX_DISCOVERED_MODELS = 1000


def model_catalogue(models: object) -> tuple[str, ...]:
    if not isinstance(models, tuple) or len(models) > MAX_DISCOVERED_MODELS:
        raise InvalidRequest("The model catalogue exceeds 1,000 entries or is invalid.")
    if any(
        not isinstance(name, str)
        or not 1 <= len(name) <= 120
        or any(char.isspace() or not char.isprintable() for char in name)
        for name in models
    ):
        raise InvalidRequest("The model endpoint returned an invalid model catalogue.")
    return tuple(sorted(set(models)))
