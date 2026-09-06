"""Project schemas onto Bedrock's documented subset without mutating local validation."""

from collections.abc import Mapping
from typing import Any

from ase.application.ports.llm import LlmGatewayError

# These remain in the application's authoritative schemas and output validators.
UNSUPPORTED_CONSTRAINTS = frozenset(
    {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "pattern",
        "maxItems",
        "uniqueItems",
        "minProperties",
        "maxProperties",
    }
)
SCHEMA_MAPS = frozenset({"properties", "$defs", "definitions"})


def project_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    visited = 0

    def visit(value: Any, depth: int = 0, *, property_map: bool = False) -> Any:
        nonlocal visited
        visited += 1
        if depth > 32 or visited > 10_000:
            raise LlmGatewayError("The response schema exceeds Bedrock's supported bounds.")
        if isinstance(value, Mapping):
            result = {}
            for key, child in value.items():
                if not property_map:
                    if key in UNSUPPORTED_CONSTRAINTS:
                        continue
                    if key == "minItems" and child not in (0, 1):
                        continue
                    if key in {"$ref", "$dynamicRef"}:
                        raise LlmGatewayError(
                            "Bedrock schema references are not supported by this adapter."
                        )
                    if key == "additionalProperties" and child is not False:
                        raise LlmGatewayError("Bedrock schemas require additionalProperties false.")
                result[key] = visit(
                    child,
                    depth + 1,
                    property_map=not property_map and key in SCHEMA_MAPS,
                )
            return result
        if isinstance(value, (list, tuple)):
            return [visit(child, depth + 1) for child in value]
        return value

    result: dict[str, Any] = visit(schema)
    return result
