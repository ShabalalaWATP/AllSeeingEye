"""Safe accounting for explicit provider output-budget exhaustion."""

from ase.application.ports.llm import LlmTokenBudgetExhausted


def budget_exhausted(
    model: object,
    usage: object,
    input_key: str,
    output_key: str,
    *,
    model_limit: int = 120,
) -> LlmTokenBudgetExhausted:
    """Malformed optional metadata must never turn exhaustion into a retry.

    Counts fit persisted signed integers. Only the validated identifier and counts
    are retained, never provider text, partial output or reasoning.
    """
    tokens: list[int | None] = []
    for key in (input_key, output_key):
        value = usage.get(key) if isinstance(usage, dict) else None
        tokens.append(value if type(value) is int and 0 <= value <= 2_147_483_647 else None)
    safe_model = (
        model
        if isinstance(model, str)
        and 1 <= len(model) <= model_limit
        and all(char.isprintable() and not char.isspace() for char in model)
        else ""
    )
    return LlmTokenBudgetExhausted(
        model=safe_model, prompt_tokens=tokens[0], completion_tokens=tokens[1]
    )
