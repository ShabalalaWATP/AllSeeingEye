"""One evidence-led global economic assessment per caller's rolling day."""

from ase.application.reports.request import ReportRequest
from ase.domain.economy_news import ECONOMIC_NEWS_IDS
from ase.domain.events import Category
from ase.domain.research import ResearchMode

COVERAGE_NOTE = (
    "One daily economic briefing from collected publisher headlines and available dated "
    "World Bank and ECB snapshots. Annual figures are historical context, not today's news; "
    "exchange reference rates are not executable market prices. Coverage can be uneven. "
    "The analysis does not read external embedded market charts."
)


def economy_briefing_request() -> ReportRequest:
    return ReportRequest(
        template_id="ask",
        question=(
            "Write a daily global economic situation report with an overall summary, latest "
            "dated developments, and clearly named sections: United Kingdom, United States, "
            "Russia, China, Iran. Cover growth, inflation, employment, monetary policy, trade, "
            "energy and financial markets only where retained evidence supports them. Explain "
            "what the developments mean in plain English for a reader new to economics. "
            "Use in-text citations and a reference list. Distinguish publisher reporting, "
            "official issuer statements, state-aligned perspectives and your own inference. "
            "Annual indicator observation periods and reference-rate dates must be explicit; "
            "their collection today is not a new economic release. Do not invent live prices "
            "or claim to have read chart widgets. Separate historical context from news in "
            "the past 24 hours. State missing or stale coverage for each country; when no "
            "material new evidence exists, say so. Add concise themes to watch, rather than "
            "buy/sell recommendations or personalised investment advice."
        ),
        categories=(Category.ECONOMIC,),
        window_hours=24,
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
        report_style="briefing",
    )
