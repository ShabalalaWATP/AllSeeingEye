"""Fixed dashboard series and honest empty states, independent of provider payloads."""

from ase.domain.economy import EconomyRegion, EconomySeries

REGIONS = (
    ("WORLD", "Worldwide", "WLD"),
    ("GB", "United Kingdom", "GBR"),
    ("US", "United States", "USA"),
    ("RU", "Russia", "RUS"),
    ("CN", "China", "CHN"),
    ("IR", "Iran", "IRN"),
)
INDICATORS = (
    ("gdp", "GDP", "NY.GDP.MKTP.CD", "Current US dollars"),
    ("growth", "GDP growth", "NY.GDP.MKTP.KD.ZG", "% annual change"),
    ("inflation", "Consumer price inflation", "FP.CPI.TOTL.ZG", "% annual change"),
    ("unemployment", "Unemployment", "SL.UEM.TOTL.ZS", "% of labour force"),
)
ECB_SOURCE = (
    "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/"
    "euro_reference_exchange_rates/html/index.en.html"
)
ANNUAL_NOTE = (
    "Annual published observations, not live market data or forecasts. "
    "Current revised snapshot; missing years remain gaps. Publication lags vary by country."
)
FX_NOTE = (
    "Currency units per 1 euro. ECB reference rates are published on working days, "
    "not live tradable quotes. A rising line means more currency units per euro."
)


def empty_regions() -> tuple[EconomyRegion, ...]:
    return tuple(
        EconomyRegion(
            region,
            name,
            tuple(
                EconomySeries(
                    key,
                    label,
                    unit,
                    "annual",
                    "World Bank",
                    f"https://data.worldbank.org/indicator/{indicator}?locations={code}",
                    "unavailable",
                    ANNUAL_NOTE + " No observations are available from this connection.",
                    None,
                )
                for key, label, indicator, unit in INDICATORS
            ),
        )
        for region, name, code in REGIONS
    )


def empty_fx() -> tuple[EconomySeries, ...]:
    return tuple(
        EconomySeries(
            currency,
            f"{currency} per euro",
            f"{currency} per EUR",
            "daily",
            "European Central Bank",
            ECB_SOURCE,
            "unavailable",
            (
                "ECB publication of the euro/ruble reference rate is suspended. "
                "No substitute or implied rate is shown."
                if currency == "RUB"
                else "The ECB does not publish an Iranian rial reference rate."
                if currency == "IRR"
                else FX_NOTE + " No observations are available from this connection."
            ),
            None,
        )
        for currency in ("GBP", "USD", "CNY", "RUB", "IRR")
    )
