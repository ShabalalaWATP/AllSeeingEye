# Honest limits

Status: draft for Alex's approval, 18 October 2026. Paths are relative to
`frontend/src/features/product/` unless they start with `docs/` or `README.md`.

The page states five limits, adapted from the "Limits to understand" section of
the repository `README.md`. They are held in `LIMITS_TEXT` (`content/platform.ts`)
and rendered by `chapters/TrustChapter.tsx` in the panel headed "What it will not
pretend", inside the "Choices and limits" section that follows the Trust chapter.

That panel is deliberately static: it is a plain `div`, not a `Reveal`, so it has
no entrance animation in any motion mode, and the chapter comment says the limits
"are deliberately plain and unanimated". It sits beside the "Bring your own AI" and
"Engineered with care" panels, which do animate in.

## The five limits

| # | KAN-171 wording | Page wording (`LIMITS_TEXT`) | README source sentence |
| --- | --- | --- | --- |
| 1 | Public sources are incomplete and can be delayed | "Public sources are incomplete and sometimes delayed, blocked or unavailable." | "Public sources are incomplete and sometimes delayed, blocked or unavailable." |
| 2 | Country-level locations are approximate | "Country-level locations are not exact event coordinates." | "Country-level locations are not exact event coordinates" |
| 3 | Calculated satellite positions are not observations | "Calculated satellite positions are not direct observations." | "calculated satellite positions are not direct observations." |
| 4 | Repeated reports are not independent confirmation | "Similar reports may share one original source and are not independent confirmation." | "Similar reports may share an original source and should not be counted as independent confirmation." |
| 5 | A model answer or a source grade does not prove a claim is true | "A source grade, a model answer or a passing check does not make a claim true." | "A source grade, model answer or passing validator does not establish that a claim is true." (README, "How AI is used") |

All five are verified against `README.md` on 18 October 2026. Limit 5 comes from
the README's "How AI is used" section rather than "Limits to understand"; the
second paragraph of "Limits to understand" makes the same point about saved
evidence and photo geolocation.

## Where else each limit appears

| # | Other places on the page |
| --- | --- |
| 1 | Sources footnote `SOURCE_CAVEAT` (`content/sources.ts`): "a catalogue entry is not a promise that a provider is available". Cyber panel limit: "Built from public reporting; it does not claim to measure all cyberattacks." |
| 2 | Tools chapter "Location quality" chips: "Source-reported exact", "Approximate", "Propagated satellite", "Not plotted" (`content/observe.ts`). Conflict layer filter "Location precision". |
| 3 | "Propagated satellite" location-quality chip. The globe's satellites are drawn on fixed illustrative rings (`scenes/sceneData.ts`, `ORBITS`), not from orbital data. |
| 4 | Collect chapter: `SHARED_ORIGIN`, "Similar reports may share one original source, so copies are grouped rather than counted as extra confirmation." (`content/research.ts`). |
| 5 | Collect grading note: "F and 6 mean the source or claim cannot yet be judged." Assess example: "Challenged: confidence held at moderate." Photo geolocation limit: "A shadow check can rule a candidate out, but it never confirms a place." |

## Workspace limits

The workspace panels (`content/platform.ts`, `WORKSPACES`) each carry at most one
limit, shown under a "Limit" label inside the panel. They move with the gallery
but have no animation of their own.

| Panel | Limit | Evidence |
| --- | --- | --- |
| Live monitoring | "Counts describe loaded reports, not verified or independently unique incidents." | `docs/CONFLICT_COVERAGE.md` counting rules |
| Ukraine | "The control map shows a reported line, not observed positions." | `docs/UKRAINE_WAR_TRACKER.md`: "this is a reported line, not observed positions" |
| Cyber intelligence | "Built from public reporting; it does not claim to measure all cyberattacks." | `docs/CYBER_THREAT_INTELLIGENCE.md` |
| Economy | "The latest available year can differ by country and measure." | `docs/ECONOMY_WORKSPACE.md`, "Compare economies" |
| Photo geolocation | "A shadow check can rule a candidate out, but it never confirms a place." | `docs/DEVELOPMENT_STORY.md` (ShadowFinder method, "never a confirmation") |
| Map tools | "Radio and terrain results are coarse planning screens, not measured reception." | `docs/MAP_WORKSPACE.md`: "None is a measurement of reception on site." |
| Teams | none | |

## Other honesty markers on the page

- "Illustrative data" chip on the globe; "Illustrative request. Nothing is sent from
  this page." (Ask); "Illustrative evidence: example sources, grades and receipts."
  (Collect); "Illustrative report. It is static text, never generated here." (Assess);
  "Illustrative screenshot" caption on the photo geolocation panel.
- "Practices, not a security certification." under "Engineered with care".
- Footer: "Scenes, questions and reports on this page are illustrative and use no
  live data."
- Production builds replace the cost estimator with a sentence saying costs are
  estimated with each organisation; development builds show "Draft figures, not yet
  reviewed." (`chapters/CostEstimator.tsx`).
