"""Native web discovery catalogue entry, separate from feed-source query budgets."""

from ase.container.research_spec import research_spec
from ase.domain.events import Category
from ase.domain.sources import SourceSpec
from ase.domain.web_research import WEB_NOTICE, WEB_SOURCE_ID, WEB_SOURCE_NAME


def web_search_spec() -> SourceSpec:
    return research_spec(
        WEB_SOURCE_ID,
        WEB_SOURCE_NAME,
        Category.NEWS,
        "A model synthesises live web-search results; generated context is not primary evidence.",
        "Explicit public-question search with the destination's OpenAI direction profile, "
        "up to three tool calls and 90 seconds per run. Output allowance follows the profile: "
        "6,000 tokens by default, up to 16,000 with reasoning headroom.",
        WEB_NOTICE,
        "Requires a compatible OpenAI Responses model and account access. "
        "Bedrock and custom OpenAI-compatible endpoints are not silently substituted. "
        "Private media and document contents are excluded. Provider usage charges may apply. "
        "Separate search selection and global source activation are both required.",
        organisation="OpenAI",
        role="aggregator",
        requires_key=True,
    )
