"""Evidence-led economic summaries for explicit, independently refreshed windows."""

from ase.application.reports.request import ReportRequest
from ase.domain.economy_news import ECONOMIC_NEWS_IDS
from ase.domain.economy_periods import EconomyWindowDays, economy_window
from ase.domain.events import Category
from ase.domain.research import ResearchMode

_COVERAGE_DETAIL = (
    "Refreshed every 24 hours using collected publisher headlines and available dated "
    "World Bank and ECB snapshots. Annual figures are historical context, not today's news; "
    "exchange reference rates are not executable market prices. Coverage can be uneven. "
    "Publisher feeds may not retain the full selected period. "
    "The analysis does not read external embedded market charts."
)


def coverage_note(days: EconomyWindowDays) -> str:
    return f"A {int(days)} day economic summary. {_COVERAGE_DETAIL}"


COVERAGE_NOTE = coverage_note(EconomyWindowDays.TWO)


def economy_briefing_request(days: EconomyWindowDays = EconomyWindowDays.TWO) -> ReportRequest:
    days = economy_window(days)
    return ReportRequest(
        template_id="ask",
        question=(
            f"Write a {int(days)} day economic summary for the exact supplied reporting range. "
            "State that range, not an unspecified timeframe. Use clear headings: "
            "Executive overview; Latest developments; United Kingdom; United States; Russia; "
            "China; Iran; Cross-country comparison; Transmission channels; What to watch; "
            "Coverage and method. Start with a concise executive paragraph. Each country "
            "starts with a short takeaway paragraph, then dated developments and implications "
            "in short paragraphs or bullets. Explain technical terms in plain English. "
            "Cover growth, inflation, employment, policy, trade, energy and markets only where "
            "evidenced. Treat dated GDP per capita, population, exports, imports, current "
            "account, central government debt, gross capital formation and manufacturing as "
            "historical context. Compare the same indicator, units and observation year in "
            "a compact table; never rank different-year values as contemporaneous. Distinguish "
            "percentage changes from percentage-point changes; do not bridge missing years. "
            "Central government debt is not general-government debt. Current-dollar GDP is "
            "nominal; per-capita output is not household income. Explain trade, currency and "
            "energy links, separating observations from hypotheses; do not infer causation "
            "from correlation. Use in-text citations and a reference list. Distinguish "
            "publisher reporting, official issuer statements, state-aligned perspectives "
            "and inference. State annual observation periods and reference-rate dates: "
            "retrieval today is not a new release. Do not invent live prices or read chart "
            f"widgets. Separate historical context from news in the selected {int(days)} days. "
            "State missing or stale country coverage and gaps in publisher archives; do not "
            "claim complete coverage. Give themes to watch, not buy/sell recommendations."
        ),
        categories=(Category.ECONOMIC,),
        window_hours=int(days) * 24,
        research_mode=ResearchMode.DETAILED,
        research_source_ids=tuple(f"research_publisher_{key}" for key in ECONOMIC_NEWS_IDS),
        research_terms=(
            "economy",
            "economic",
            "inflation",
            "GDP",
            "interest rate",
            "trade",
            "tariff",
            "employment",
            "growth",
            "bank",
            "oil",
            "market",
        ),
        report_style="assessment",
    )
