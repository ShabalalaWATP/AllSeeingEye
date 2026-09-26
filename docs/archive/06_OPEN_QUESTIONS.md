# Open Questions for Alex

Status: on 3 September 2026 Alex accepted the plan and every recommendation below, with two amendments: the 3D globe is the default view, and the logo is specifically the React Bits Evil Eye component (https://reactbits.dev/backgrounds/evil-eye). The recommended answers are therefore the decisions of record. Questions 13, 16, 19 and 20 (hardware, seed content, user count, ops-room screen) are still open and run on the stated defaults until answered.

Each question below keeps its options and recommendation for the record.

## A. Decisions that change the build

1. **Where will it run, and who can reach it?** Options: (a) your Windows PC with Docker Desktop, LAN or Tailscale only; (b) a home server or NAS; (c) exposed to the internet. Recommendation: (a) or (b) behind Tailscale. Internet exposure is possible later but brings HSTS, a public domain, stricter rate limits and a proper backup discipline before it is safe.

2. **Globe engine.** MapLibre GL JS 6 with deck.gl (one engine for globe and map, small, free) or CesiumJS (true 3D, 6 MB core, imperative API). Recommendation: MapLibre. See ADR 0001.

3. **Database.** PostgreSQL 16 with PostGIS in Docker, or SQLite. Recommendation: PostgreSQL. See ADR 0002.

4. **Live data tier.** In-memory bounded store in the API process, or Redis. Recommendation: in-memory behind a port; Redis only if collectors are split out later. See ADR 0003.

5. **Which LLM endpoints will you actually use?** A local model (Ollama, LM Studio, vLLM) and/or a hosted one (OpenRouter, OpenAI, Groq, Mistral). This decides context budgets, whether JSON schema output can be relied on, and whether an embeddings endpoint exists. Recommendation: design for both, test with one local and one hosted profile, and route translation and classification to a cheap model and assessments to the strongest one.

6. **Local NLP on the server.** Allow a small local model for embeddings and named entities (about 250 MB RAM, CPU only), or keep the backend free of machine learning and use hashing-based deduplication plus the LLM endpoint for anything semantic. Recommendation: start without local models; add them as an optional adapter if clustering quality disappoints.

7. **Telegram.** Public conflict channels are valuable but every route has a cost: the Bot API cannot read channels it does not administer; the MTProto client (Telethon) needs your personal account and carries ban and terms-of-service risk; the public `t.me/s/channel` preview pages need no account but are unofficial and fragile. Recommendation: leave Telegram out of the first release, then add the preview-page connector as an opt-in with a clear warning.

8. **Scraping policy.** Only official feeds and APIs, or also HTML scraping of sites that offer neither. Recommendation: feeds and APIs only. It keeps the app polite, the connectors simple and the licence position clean; the catalogue already has more free feeds than we can use.

9. **Doctrine specifics.** Confirm: the 2025 PHIA yardstick bands; Analytical Confidence Ratings (High, Moderate, Low) with the three-factor statement; the NATO A to F and 1 to 6 grading; the INTSUM-style structure in `03_DOCTRINE_AND_REPORTING.md` (APP-11 formats are restricted, so these headings are doctrine-consistent proposals). Do you want the US ICD 203 vocabulary available as an alternative? Recommendation: UK only.

10. **Report export.** Client-side PDF via a print stylesheet and DOCX via the `docx` library in the browser, or server-side rendering. Recommendation: client-side; it avoids native PDF toolchains on Windows and keeps the API small.

11. **Email.** Do you have an SMTP provider for password resets and alerts (a Gmail app password, Brevo or Resend free tiers)? If not, the admin issues reset links from the admin page and alerts go in-app and to webhooks. Recommendation: start without SMTP; add it when you want emailed reports.

12. **Repository and licence.** Private GitHub repository? Licence for the code (MIT, Apache 2.0, or all rights reserved)? Several data sources are non-commercial only, which is fine for a hobby product but matters if the code is ever published with a permissive licence and a "run it yourself" pitch. Recommendation: private repo, decide the licence later.

13. **Host hardware.** RAM, CPU and GPU of the machine that will run the backend and the browser. This sets the live store budgets and whether local NLP is sensible.

## B. Free accounts and keys to obtain (all free; nothing is needed for Phase 0)

| Phase | Service | What to get |
|---|---|---|
| 1 | OpenSky Network | Account plus an OAuth2 API client (4,000 credits per day) |
| 1 | NASA FIRMS | MAP_KEY by email |
| 1 | OS Data Hub | OpenData plan project with the OS Maps API enabled (key stays server-side) |
| 1 | ReliefWeb | Pre-approved application name (required since November 2025) |
| 2 | Internet Archive | S3-style keys for Save Page Now (evidence archiving) |
| 3 | UCDP | Access token requested from the maintainers |
| 3 | ACLED | myACLED account. With a Gmail address you get the aggregated "Open myACLED" tier; event-level data appears to need an institutional email, so tell me if you have one |
| 3 | AISStream.io | API key (GitHub sign-in) |
| 3 | Global Fishing Watch | API token |
| 3 | alerts.in.ua | Token via their form |
| 3 | Cloudflare Radar | Account plus a token with Radar read permission |
| 5 | YouTube | A Google Cloud project with the YouTube Data API v3 enabled and an API key restricted to it, set as `ASE_YOUTUBE_API_KEY`. Without it there is no YouTube collection at all: `youtube.com/robots.txt` disallows the channel Atom path this application used to poll, so those nine feeds were retired on 16 September 2026 and rebuilt on the API. The default 10,000 units a day covers the 29 packaged channels (about 1,392 units) and the capped 40 video searches (4,000 units) with room to spare |
| 5 | Reddit | **Decision needed, nothing is built.** `reddit.com/robots.txt` is `User-agent: *` then `Disallow: /` for every path, so the three subreddit feeds were retired on 16 September 2026. The only compliant route is a registered OAuth application under Reddit's Public Content Policy: an account with two-factor authentication, a "script" app at `reddit.com/prefs/apps`, agreement to the Data API Terms in your own name, and a keyed connector reading `oauth.reddit.com` (free tier: 100 queries per minute). Say if you want it; it is not assumed |
| Optional | N2YO, OpenAQ, Met Office DataHub, HDX HAPI identifier, IOM DTM, ACAPS, Metaculus | Keys only if those features are switched on |

## C. Preferences that can default

14. **Nation filter semantics.** By event location only, or also by actor (for example Russian military aircraft anywhere)? Recommendation: location first, actor as a second filter where the data supports it (aviation, maritime, sanctions).

15. **Name and look.** "The All Seeing Eye" as the product name, with `ase` as the code name. The React Bits eye defaults to an ember orange (`#FF6F37`); the accent could follow the eye (ember) or shift to crimson. Recommendation: keep the accent tied to the eye colour so the login page and the app read as one identity, and use cyan for live data and amber for warnings.

16. **Seed content.** Which conflicts and areas should ship pre-configured (Ukraine, Gaza and Lebanon, Sudan, Sahel, DRC, Myanmar, Yemen and the Red Sea, Taiwan Strait, Korea, Haiti are the obvious set)? Which UK areas of interest matter to you?

17. **Units and time.** UTC everywhere with a local-time toggle; nautical miles, knots and feet for aviation and maritime, kilometres elsewhere. OK?

18. **Handling caveat wording.** Reports need a banner. Suggestion: "OPEN SOURCE / MACHINE-GENERATED ASSESSMENT / REVIEW BEFORE USE". Any preferred wording?

19. **How many users?** Family and friends (under ten) is the assumption behind the rate limits and the single-process design.

20. **Ops room display.** Is there a wall screen or TV you want the idle mode designed for (resolution, viewing distance)?
