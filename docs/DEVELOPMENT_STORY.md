# Development Story

A concise, chronological record of how The All Seeing Eye is being built. Maintained by the development-story keeper; newest entries at the bottom.

## 2 September 2026: design

- Alex asked for a full design for an AI OSINT fusion app: a 3D globe as the primary view with a map mode (OS Maps, satellite, hybrid), free data sources across news, social, foreign-language media, aviation, disasters and more, LLM-written reports following the British probability yardstick and NATO intelligence doctrine with graded sources, two roles, a login flow with account requests and password reset, dark mode throughout, SOLID and secure by design, and the React Bits Evil Eye as branding.
- Four research passes verified the mapping stack (MapLibre GL JS 6 globe, OS Data Hub free tier, satellite and dark base maps, the Evil Eye component), about 120 free data sources across every category, and the doctrine (PHIA 2025 yardstick and confidence ratings, JDP 2-00 fourth edition, NATO AJP-2 and AJP-2.1, ICD 203, the NATO OSINT Handbook, the Berkeley Protocol).
- The proposal was written as eight documents plus seven ADRs under `docs/`, and published as a summary page. Key ideas: one unified Event model; a bounded in-memory live tier with evidence freezing as the only path to durable storage; deterministic grading before generation; a validator that enforces the yardstick, confidence ratings and citations; the intelligence cycle as the product's information architecture.

## 3 September 2026: approval and Phase 0 start

- Alex approved the plan and every recommendation with two amendments: the 3D globe is the default view for every session, and the logo is specifically the React Bits Evil Eye component. The ADRs moved to Accepted; the open questions record the recommended answers as decisions.
- Toolchain check on the Windows 11 host: git 2.51, Python 3.13, uv 0.11, Node 22, npm 11 and the Docker CLI present; pnpm installed at user level through npm because corepack could not write its shims without administrator rights; `just` and `pre-commit` absent (run through `uvx` or install with `uv tool`); the Docker daemon not running, so PostgreSQL via compose stays unverified until it is started.
- Repository initialised on `main` with the approved documents, the project `CLAUDE.md`, the Phase 0 auth API contract (`docs/api/AUTH_API.md`) and the master implementation plan as the first commit.
- Two implementation workers were launched in parallel on disjoint paths (backend plus root infrastructure; frontend). The first attempt was cut short by a usage limit before either wrote code; both were relaunched once the limit reset.
