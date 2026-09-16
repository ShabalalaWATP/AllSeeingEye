"""Operator-configured token prices, used only to estimate spend from recorded tokens.

This is never a billing figure.  The ledger records tokens, not invoices: a provider's
own accounting may differ through rounding, cached input, minimum charges, discounts or
prices that changed mid-period.  Prices default to the model the operator runs today and
are expected to be edited when that changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

MAX_PRICE_PER_MILLION = Decimal("10000")
PER_MILLION = Decimal(1_000_000)
# Four decimal places: a single mechanical call can cost well under a penny.
CENTS = Decimal("0.0001")


def _price(value: float | Decimal, label: str) -> Decimal:
    price = Decimal(str(value))
    if not price.is_finite() or price < 0 or price > MAX_PRICE_PER_MILLION:
        raise ValueError(f"The {label} token price must be between 0 and {MAX_PRICE_PER_MILLION}.")
    return price


@dataclass(frozen=True, slots=True)
class AiTokenPrices:
    """Price per million tokens, held exactly so an estimate does not drift."""

    input_per_million: Decimal
    output_per_million: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if len(self.currency) != 3 or not self.currency.isupper() or not self.currency.isalpha():
            raise ValueError("The price currency must be a three letter code such as USD.")

    @classmethod
    def of(
        cls,
        input_per_million: float | Decimal,
        output_per_million: float | Decimal,
        currency: str = "USD",
    ) -> AiTokenPrices:
        return cls(
            _price(input_per_million, "input"), _price(output_per_million, "output"), currency
        )

    @property
    def configured(self) -> bool:
        """False when both prices are zero, so no spend is estimated and none is shown."""
        return bool(self.input_per_million or self.output_per_million)

    def estimate(self, input_tokens: int, output_tokens: int) -> Decimal | None:
        """Estimated spend for already recorded token counts, rounded to four places."""
        if min(input_tokens, output_tokens) < 0:
            raise ValueError("Token counts cannot be negative.")
        if not self.configured:
            return None
        total = (
            Decimal(input_tokens) * self.input_per_million
            + Decimal(output_tokens) * self.output_per_million
        ) / PER_MILLION
        return total.quantize(CENTS, rounding=ROUND_HALF_UP)
