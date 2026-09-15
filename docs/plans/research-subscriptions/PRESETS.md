# Preset implementation specification

This is part of R03 in the [shared brief packet](03-briefs-and-presets.md). All twenty entries below are approved scope. Source names here are **proposed bundles**, not newly verified API integrations. Resolve each to existing catalogue capability IDs or explicit gaps in E00; E03 adds missing supported routes and live verification. Never invent an ID or claim a source was searched because its name appears here.

## Common rules

- Each entry expands into editable question, requirement IDs, geography, languages, source policy, lens, observation period, horizon, sections and indicators.
- Default depth: Deep. Default baseline: seven days; forecast horizon: next 30 days only where forecasting is useful. Subscription cadence is the user's choice, not hard-coded by the preset.
- Annual/quarterly editions use the requested interval and retained/historical coverage, not the seven-day baseline. Baseline lookback is for first activation only.
- All reports include key judgements, supporting findings, opposing evidence, gaps and references. Extra sections below supplement that common structure.
- Authoritative issuer status can establish that a statement was made. It does not establish the truth of every assertion in it. Do not rank by nationality or by agreement with the selected lens.
- Languages are search suggestions; distinguish source language, query language and report output language. Keep original passages beside translation provenance.
- A quiet period is legitimate. No preset requires inventing a development or a forecast.
- Each indicator is a watch question with a cited observable condition, not an automatically verified alert. Actor attribution, damage claims and casualty figures require explicit provenance and uncertainty.

## Reusable source bundles

| Bundle | Intended content and gap handling |
| --- | --- |
| NEWS | Existing UK/world/regional publisher and multilingual discovery adapters. Retrieve permitted original passages through E02; disambiguate syndication. |
| OFFICIAL | Relevant government, parliament, diplomacy and institutional releases already registered. Add missing official routes only after documentation/terms verification. Party claims remain attributed. |
| CONFLICT | Existing conflict adapters/catalogue, available ACLED route, humanitarian reporting and NEWS/OFFICIAL. ACLED is a declared setup gap when unavailable. No automatic claim that every coded incident is armed conflict. |
| HUMANITARIAN | Existing UN/ReliefWeb RSS, optional approved ReliefWeb API, IFRC and disaster sources. Keep appeals, forecasts and observed impacts separate. |
| CTI | Existing NCSC/CISA and other supported national CERT/vendor feeds; existing ATT&CK actor reference catalogue; vulnerabilities/exploitation records. Distinguish historical actor knowledge from current observed activity. |
| NETWORK | Existing IODA, Cloudflare Radar and supported connectivity sources through typed research bridges. Country-level aggregates are not incident locations or attacker identities. |
| MACRO | Existing economic adapters, plus verified ONS/ECB routes where missing. Central bank/national statistical releases, World Bank/IMF/OECD capabilities when supported. Store dates, units, revisions and frequency. |
| TRADE | Existing trade, sanctions, corporate/filing and shipping sources. Missing Companies House, sanctions snapshots or other setup remains visible. Registries establish recorded filings, not hidden beneficial ownership. |
| ENERGY | Supported energy statistics and institutional releases, filings and NEWS. Distinguish spot/futures prices, physical flow, installed capacity and available capacity. |
| MOBILITY | Existing permitted AIS/aviation/port datasets and observed track snapshots. Public tracking is incomplete; absence from a receiver is not evidence of no movement. |
| HAZARD | Existing FIRMS, earthquake/weather/disaster and humanitarian adapters. Separate sensor detections, model forecasts and confirmed impacts. |
| SCHOLARLY | Existing OpenAlex and selected permitted papers/documents for background; publication is not immediate event verification. |
| AREA | Applicable mapped source adapters and precise AOI matching, plus country-level context explicitly labelled. No fabricated precision from place mentions. |

## Conflict briefs

### P01: global conflict briefing (`conflict-global`)

Question: Which armed conflicts changed materially during the selected period, and what are the implications over the next month?

Required questions: major evidenced developments; changes in intensity/territorial claims; civilian and humanitarian effects; diplomacy/escalation indicators. Scope: global, with a disclosed relevance/coverage selection. Languages: English plus languages of selected regions, within budget. Sources: CONFLICT, HUMANITARIAN, NEWS, OFFICIAL. Extra sections: prioritised regional table, sourced timeline and coverage gaps. Indicators: corroborated escalation, ceasefire changes, displacement or aid-access deterioration. Exclude ordinary crime/accidents from armed-conflict classification; separately label relevant civil unrest.

### P02: Russia and Ukraine (`conflict-russia-ukraine`)

Question: Assess developments in the Russia–Ukraine war, distinguish claims from corroborated reporting and explain implications for security, civilians and diplomacy.

Required questions: significant developments and contested claims; civilian/infrastructure effects; military-economic constraints; diplomatic and escalation indicators. Scope: Russia/Ukraine and explicitly relevant spillover. Languages: English, Ukrainian, Russian. Sources: CONFLICT, HUMANITARIAN, OFFICIAL, NEWS, ENERGY where relevant. Extra sections: dated developments, disputed assessments and implications for the chosen lens. Indicators: cited policy/ceasefire changes, documented civilian effects or supply disruption. Preserve provenance of map/frontline changes and avoid representing dated assessments as live positions.

### P03: Israel, Gaza and the West Bank (`conflict-israel-gaza-west-bank`)

Question: Assess developments affecting security, civilian protection, aid access and diplomacy in Israel, Gaza and the West Bank during the selected period.

Required questions: reported events with attribution; civilian effects and aid access; statements/actions by parties; diplomatic developments and alternative explanations. Scope: Israel, Gaza and West Bank, with regional context explicitly distinguished. Languages: English, Arabic, Hebrew. Sources: CONFLICT, HUMANITARIAN, OFFICIAL, NEWS. Extra sections: separate observed reporting, party claims, assessed implications and unresolved contradictions. Lens options include civilian protection, Israeli domestic/security concerns, Palestinian civilian/governance concerns and regional diplomacy. Indicators: documented access changes, agreement implementation, corroborated escalation or displacement. No lens may erase contrary evidence or equate different actors' claims without examining their support.

### P04: Iran and regional escalation (`conflict-iran-region`)

Question: What developments involving Iran materially change regional escalation risk, diplomacy or civilian and economic exposure?

Required questions: attributed activities; diplomatic/official signals; energy/shipping consequences; competing escalation/de-escalation explanations. Scope: Iran plus named relevant neighbouring areas. Languages: English, Persian, Arabic. Sources: CONFLICT, OFFICIAL, NEWS, ENERGY, MOBILITY. Extra sections: actor claims, regional dependencies and indicators. Indicators: verified policy change, shipping disruption or multilateral reporting; distinguish intention assessments from observations.

### P05: Taiwan and the Indo-Pacific (`conflict-taiwan-indopacific`)

Question: Which developments affect Taiwan Strait and wider Indo-Pacific security, and how should they change the current outlook?

Required questions: reported activity and official policy; regional diplomacy; trade/supply-chain implications; alternative explanations and warning indicators. Scope: Taiwan Strait plus explicitly selected regional actors. Languages: English, Chinese, Japanese, Korean as supported and relevant. Sources: OFFICIAL, NEWS, TRADE, CONFLICT, MOBILITY. Extra sections: dated activity versus routine baseline, diplomacy and commercial exposure. Indicators: evidenced policy or sustained-pattern changes; public track gaps alone do not establish military activity.

## Cyber briefs

### P06: global cyber threat intelligence (`cyber-global`)

Question: Which evidenced cyber developments matter most to defenders during this period?

Required questions: active exploitation; reported campaigns and attribution; affected sectors/regions; prioritised defensive implications. Languages: English plus relevant incident-source languages. Sources: CTI, NETWORK, NEWS. Extra sections: exploitation table with advisory dates, actor/campaign distinction and source disagreements. Indicators: new corroborated exploitation, authoritative urgent advisory or material campaign change. No automatically generated offensive actions or active scanning.

### P07: UK critical sectors (`cyber-uk-critical-sectors`)

Question: Assess cyber developments relevant to selected UK critical sectors and identify evidence-backed defensive priorities.

Required input: one or more sectors, optional voluntary technology profile. Requirements: relevant incidents/advisories; exploitation affecting selected assets; third-party dependencies; confidence and defensive implications. Sources: CTI, NETWORK, OFFICIAL, NEWS. Languages: English, optional original advisory languages. Extra sections: relevance matrix and evidence-backed prioritisation. Indicators: affected product in profile, observed exploitation or verified service disruption. Profile matching means potential relevance, not proof the user's systems are vulnerable.

### P08: ransomware (`cyber-ransomware`)

Question: What changed in ransomware activity, affected sectors and defensive exposure during the period?

Requirements: corroborated incidents; claimed versus confirmed victims; campaign/tool changes from trusted analysis; defensive implications. Sources: CTI, NEWS, official victim/disclosure statements through safe acquisition. Languages: English plus selected regions. Extra sections: claim/corroboration table and sector trends with denominators. Indicators: corroborated campaign change or exploitation route. Do not collect leaked personal files or treat criminal leak-site assertions as confirmed incidents.

### P09: selected threat actor (`cyber-actor-watch`)

Required input: reviewed actor ID or an explicit ambiguous-name resolution. Question: What new evidence changes our understanding of this actor's reported activity and defensive relevance?

Requirements: new campaign reports; attribution basis and uncertainty; observed techniques versus historical reference; defensive implications for selected sectors. Sources: CTI, NEWS, OFFICIAL. Languages: English plus relevant originals. Extra sections: alias/source crosswalk, historical versus current timeline. Indicators: new independent attribution evidence or validated campaign change. ATT&CK descriptions alone are background, not proof of current operation or location.

### P10: exploitation affecting selected technologies (`cyber-technology-exploitation`)

Required input: product/vendor/version or technology family. Question: Which current exploitation evidence and advisories are relevant to these technologies?

Requirements: affected versions; observed versus hypothetical exploitation; patch/mitigation status from issuer; dependency/sector implications. Sources: CTI and vendor originals. Extra sections: CVE/product/version table, first-seen/advisory dates, uncertainty on inventory matches. Indicators: confirmed exploitation, revised affected versions or changed remediation guidance. Do not imply version-name similarity proves exposure.

## Economic briefs

### P11: global macroeconomy (`economy-global`)

Question: What changed in global growth, inflation, financial conditions and trade, and through which mechanisms might it matter next?

Requirements: relevant releases/revisions; monetary/fiscal changes; trade/energy conditions; transmission mechanisms and alternative outlooks. Sources: MACRO, ENERGY, TRADE, NEWS. Languages: English plus original institutional languages where useful. Extra sections: comparable indicator table, release calendar and sourced charts. Indicators: defined data surprises/revisions or policy changes. Avoid merging incompatible frequencies, nominal/real measures or revised vintages.

### P12: UK economy (`economy-uk`)

Question: Assess changes in UK growth, prices, employment, monetary/fiscal policy and external exposure.

Requirements: official releases and revisions; Bank of England/Treasury policy; household/business transmission; trade/energy implications. Sources: MACRO (ONS and UK official routes prioritised), ENERGY, TRADE, NEWS. Language: English. Extra sections: UK dashboard, dated releases and short written interpretation. Indicators: selected inflation/labour/growth releases and policy decisions, with release date separated from the period measured.

### P13: USA economy (`economy-usa`)

Question: Assess changes in US activity, prices, labour markets, policy and global spillovers.

Requirements: relevant statistical releases/revisions; Federal Reserve/fiscal developments; trade/financial transmission; alternative outlooks. Sources: MACRO, TRADE, NEWS with verified US official routes. Language: English. Extra sections: indicators and transmission chart where data supports it. Indicators: named release/policy changes, not trading recommendations or promised price predictions.

### P14: China economy (`economy-china`)

Question: Assess changes in China's activity, prices, property/credit conditions, policy and trade exposure.

Requirements: official data with methodological limits; policy implementation evidence; property/credit and external demand; corroborating/contrary indicators. Sources: MACRO, TRADE, NEWS, OFFICIAL. Languages: English, Chinese. Extra sections: source comparison, series limitations and policy transmission. Indicators: evidenced credit/property/trade shifts or policy changes. Government statements and external estimates retain distinct definitions and provenance.

### P15: Russia economy (`economy-russia`)

Question: Assess changes in Russia's economic conditions, fiscal/monetary policy, energy trade and sanctions exposure.

Requirements: available official data/revisions; energy/trade evidence; budget/price/monetary changes; sanctions and data gaps. Sources: MACRO, ENERGY, TRADE, NEWS, OFFICIAL. Languages: English, Russian. Extra sections: reported versus independently estimated measures, trade/methodology caveats. Indicators: documented restrictions, release revisions or evidenced trade shifts. Missing data is not inferred stability.

### P16: Iran economy (`economy-iran`)

Question: Assess changes in Iran's prices, activity, fiscal/monetary conditions, energy trade and external constraints.

Requirements: official and alternative data definitions; exchange-rate regime distinctions; energy/trade/sanctions developments; civilian/business implications. Sources: MACRO, ENERGY, TRADE, NEWS, OFFICIAL. Languages: English, Persian. Extra sections: currency/price methodology, data gaps and transmission. Indicators: evidenced policy or trade changes; never treat official and market FX series as interchangeable.

## Cross-cutting briefs

### P17: energy security (`energy-security`)

Required input: region and optional commodity. Question: What changed in energy supply, demand, infrastructure disruption and policy exposure?

Requirements: sourced physical/pricing indicators; reported outages/disruptions; policy/trade changes; alternative explanations and exposure. Sources: ENERGY, TRADE, NEWS, OFFICIAL, HAZARD where relevant. Languages: English plus region. Extra sections: supply/dependency table and comparable series charts. Indicators: confirmed facility/flow disruption or policy change. Infrastructure capacity does not prove current output.

### P18: shipping and supply chains (`shipping-supply-chains`)

Required input: routes/regions, optional commodity/sector. Question: What evidenced disruptions or changes affect the selected maritime and supply-chain dependencies?

Requirements: port/chokepoint developments; available movement/volume indicators; trade/regulatory changes; downstream exposure. Sources: MOBILITY, TRADE, NEWS, OFFICIAL, HAZARD. Languages: English plus selected regions. Extra sections: route/dependency map and coverage table. Indicators: corroborated closure/disruption or measured change with a valid baseline. AIS coverage and receiver changes must not be reported as fleet-wide movement changes.

### P19: disasters and humanitarian conditions (`disaster-humanitarian`)

Required input: global relevance briefing or selected regions/hazard types. Question: What verified or reported hazards and humanitarian impacts changed, and what remains uncertain?

Requirements: hazard observations; exposure versus confirmed impacts; aid/access/displacement reporting; forecast and coverage limits. Sources: HAZARD, HUMANITARIAN, NEWS, OFFICIAL. Languages: English plus affected regions. Extra sections: event/impact/response table with observation dates, sourced timeline. Indicators: authority-issued alert, confirmed impact update or aid-access change. FIRMS detections alone are not confirmed destructive fires or attacks.

### P20: custom area watch (`area-custom`)

Required input: valid saved polygon/shape and main question. Question: What relevant developments are evidenced within this area, and what wider context affects it?

Requirements: area-matched observations; relevant news/infrastructure context; developments against the operator's themes; gaps and uncertainty. Sources: AREA plus user-selected bundles. Languages: derive suggestions from geography, allow edits. Extra sections: exact AOI map, precise versus regional-context table and requirements matrix. Indicators: user-defined observable changes. Preserve map geometry and provider disclosure choice; approximate mentions remain context and never become precise incident markers.

## Catalogue acceptance

For every preset, test schema, required inputs, source-capability resolution, language fallback receipts, brief round trip and at least one domain-specific quality trap above. Expose last review date and source-readiness summary. A disabled preset with unresolved implementation is pending work; a usable preset with a transparently unavailable optional provider can still operate with an honest coverage limitation.
