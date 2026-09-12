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
    ("gdp_per_capita", "GDP per capita", "NY.GDP.PCAP.CD", "Current US dollars"),
    ("population", "Population", "SP.POP.TOTL", "People"),
    ("exports", "Exports of goods and services", "NE.EXP.GNFS.ZS", "% of GDP"),
    ("imports", "Imports of goods and services", "NE.IMP.GNFS.ZS", "% of GDP"),
    ("current_account", "Current account balance", "BN.CAB.XOKA.GD.ZS", "% of GDP"),
    ("government_debt", "Central government debt", "GC.DOD.TOTL.GD.ZS", "% of GDP"),
    ("investment", "Gross capital formation", "NE.GDI.TOTL.ZS", "% of GDP"),
    ("manufacturing", "Manufacturing value added", "NV.IND.MANF.ZS", "% of GDP"),
)
ANNUAL_PERIODS = 12
INDICATOR_NOTES = {
    "gdp": "Current-dollar GDP is nominal, not an inflation-adjusted growth measure.",
    "gdp_per_capita": "Output per person in current US dollars, not wages or household income.",
    "exports": "Goods and services exported, as a share of GDP; not goods alone.",
    "imports": "Goods and services imported, as a share of GDP; not goods alone.",
    "current_account": "Includes trade, primary income and transfers; not the trade balance alone.",
    "government_debt": "Central government only, not consolidated general-government debt. "
    "Institutional coverage and reporting years can differ between countries.",
    "investment": "Gross capital formation includes fixed assets and changes in inventories, "
    "not purchases of financial investments.",
    "manufacturing": "Manufacturing value added, not all industry or total industrial output.",
}
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
                    annual_note(key) + " No observations are available from this connection.",
                    None,
                )
                for key, label, indicator, unit in INDICATORS
            ),
        )
        for region, name, code in REGIONS
    )


def annual_note(indicator_id: str) -> str:
    return " ".join(part for part in (ANNUAL_NOTE, INDICATOR_NOTES.get(indicator_id, "")) if part)


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
