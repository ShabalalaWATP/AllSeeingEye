# Development story

## 18 July 2026: routed expert-board foundation

- Inspected the complete Electron main, preload, renderer, capture, prompt, schema, state and test flows, then visually checked the running packaged app.
- Established a baseline: type checks and build passed; one stale window-position test failed because it expected an old eye size.
- Ran eight parallel, read-only research tracks for Cyber Security, UX, Finance, Legal, Policy, Ethics, Technical Architecture and Product Differentiation.
- Verified the OpenAI Responses API structured-output pattern against current official documentation.
- Kept orchestration in the Electron main process. No remote backend, database, runtime web retrieval or new dependency was added.
- Added an observation/router stage so the raw screenshot is sent once. Selected experts receive a bounded evidence envelope.
- Added eight versioned knowledge packs with authoritative source IDs, jurisdictions, binding status, verification dates, rubrics, exclusions and disclaimers.
- Added Focused and Combined review depths. Combined runs only relevant experts and synthesises validated outputs while preserving disagreement.
- Added an optional screen or text focus question, a visible Ask control, an Ask tab, context-menu access, source-aware expert details and selected-expert chips.
- Added local identity, version and citation allow-list sanitisation.
- Improved keyboard activation, dynamic status semantics, explicit field labels, reduced motion and persistent all-clear results.
- Corrected the stale geometry test and added orchestration and knowledge-pack tests.
- Final verification for this milestone: 74 tests passed, type checks passed and production build passed.

## 18 July 2026: relevant-only inputs and expert workspaces

- Added Writing & Editorial Quality, Evidence & Research Quality, and Delivery & Operations, bringing the versioned board to eleven experts.
- Replaced model-selected expert IDs with typed, evidence-linked routing signals and a deterministic local relevance policy. Added forbidden-route tests so a generic business or SaaS proposal does not summon Cyber or Architecture.
- Required expert findings to cite valid evidence IDs, reconstructing visible evidence locally. Abstaining experts cannot return findings and are removed before synthesis.
- Added stable run IDs. A new result opens **Overall** once, then preserves navigation across state updates.
- Replaced nested expert disclosures with a first-class Overall review and a unique tab for each contributing expert only.
- Added the eye hover/focus launcher for Display, Application window, Text idea and Voice note.
- Added local display/window previews with expiring opaque tokens, exact source matching and fail-closed capture when a source disappears.
- Added bounded, audio-only voice recording and OpenAI transcription. Users review and edit the transcript before analysis; automatic transcript punctuation does not automatically invoke Writing.
- Added strict IPC sender validation and audio-only Electron permission handlers. Responses requests now set `store: false`.
- Verification after security review: 85 tests passed, both type-check targets passed, the production build and unpacked Windows package passed, and the production dependency audit reported zero vulnerabilities.

## 18 July 2026: input chooser usability pass

- Diagnosed the reported right-click menu as a stale portable build and made the current source choices unambiguous.
- Changed the native menu to expose display, application-window, quick-text and voice-note inputs as four direct actions, with quick display analysis kept as a separate shortcut action.
- Reordered each composer around the input first and moved expert lens and Focused/Combined depth into a secondary review-setup section.
- Added a quick-note heading, autofocus and clearer submit wording, aligned the eye launcher labels with the native menu, and increased the idle eye from 200×150 to 216×160.
- Required an explicit screen or window card selection in normal sharing flows, added a clear source-expiry state, and kept display-under-pointer capture as a separate quick action.
- Replaced the decorative input hint with a keyboard-operable chooser, kept it outside the live-status semantics, and aligned its expanded state with the launcher.
- Final verification: 85 tests and both TypeScript targets passed; the production build, preflight, dependency audit and portable packaging passed; the rebuilt Windows UI exposed all four native-menu choices and the display, window, text and voice composers correctly.

## 18 July 2026: deliberate right-click chooser

- Removed hover and focus activation from the eye input launcher.
- Restored a normal left-click as the quick display-under-pointer analysis.
- Made right-click toggle the compact four-choice Screen, Window, Text note and Voice note launcher, with Escape, focus loss or choosing an option dismissing it.
- Kept the fuller native operational menu in compact and expanded panel modes so Pause, Hide and Quit remain available.
- Verification: hover produced zero chooser controls; right-click exposed exactly four accessible controls and no native menu items; a second right-click closed the launcher. Both TypeScript targets, 85 tests, whitespace checks and portable Windows packaging passed.

## 18 July 2026: health reasoning and automatic voice analysis

- Reproduced the 8pm cappuccino failure and traced it to the absence of health/sleep routing, a generic Evidence fallback and an expert prompt that suppressed stable model background knowledge.
- Added Health, Sleep & Wellbeing as the twelfth routed specialist, with ordinary sleep/caffeine signals separated from urgent health red flags so a late coffee produces proportionate advice rather than an emergency classification.
- Extended knowledge packs with short, source-linked factual notes. The initial Health pack includes current NHS, NICE, FSA and EFSA guidance on caffeine, sleep, individual variation, persistent insomnia and escalation boundaries.
- Updated expert policy to combine curated notes with stable, widely accepted model background knowledge. Model-only propositions cannot receive a pack citation, and volatile, high-stakes or personalised claims require verification and lower confidence.
- Replaced the voice sequence of Stop, Transcribe, edit and Analyse with one Record → Done → Transcribing → Analysing flow. The main process holds one gate across both model phases, then clears its audio view and transcript reference.
- Kept an optional focus question visible before recording, and retained bounded audio-only capture, explicit recording consent, auto-stop, size limits, pre-send cancellation and automatic-transcript protection from surface grammar review.
- Added strict combined voice-request validation plus routing, pack, citation and state regressions. The configured production model passed a live evaluation of “Should I have a caffeinated cappuccino at 8pm if I want to sleep tonight?”.
- Final verification: 94 deterministic tests passed with one opt-in live test skipped by default; the live model test passed separately; both TypeScript targets, production build and portable Windows packaging passed. The rebuilt Voice panel was inspected without requesting microphone permission.

## 18 July 2026: clean idle eye and attached input tray

- Removed all visible status and instructional text from the idle eye surface while preserving an assistive-technology live status.
- Changed the four input actions to appear in a compact tray beneath the still-visible eye after a short hover delay or keyboard focus. Right-click remains a fallback for opening the same tray.
- Added delayed close behaviour so the pointer can move naturally from the eye into the tray, Escape restores focus to the eye, and reduced-motion preferences remain respected.
- Added a main-process eye-tray size rather than leaving a large invisible always-on-top hit area beneath the idle eye.
- Reserved the tray-safe desktop footprint when positioning or saving the eye, preventing the eye from jumping when the tray opens near a screen edge.
- Verification: 95 deterministic tests and both TypeScript targets passed; production build and portable packaging passed. The rebuilt idle eye and attached four-action tray were inspected visually, including Escape closing without reopening.

## 18 July 2026: quick take before expert analysis

- Split every input into a direct general-model quick take followed by an optional full expert review. The quick schema contains only one bounded answer and cannot present severity, confidence, citations or expert coverage.
- Added a UUID-bound, single-use input hand-off in the main process with an active five-minute lifetime. Full analysis reuses the exact selected pixels, text or voice transcript rather than capturing or transcribing again.
- Voice now requests microphone access and begins recording as soon as Voice note is deliberately selected. Done sends the recording for transcription and the quick take with no setup screen or second submission.
- Removed expert mode and depth controls from the initial Text, Screen, Window and Voice surfaces. Specific visual and text questions remain available through a closed disclosure, while Focused or Combined expert depth appears only beside the quick result.
- Added a UUID-bound main-process recording reservation so screen shortcuts and Pause cannot silently compete with an active voice note. Pause, dismissal and component teardown stop the media tracks and release the reservation.
- Renderer audio is cleared after IPC hand-off, main-process audio copies are cleared after transcription, and raw full-review input is dropped immediately after observation. Pending source references are also dropped on expiry, dismissal, pause, replacement, expansion and quit.
- Final verification: 110 deterministic tests passed with one credential-dependent live test skipped; both TypeScript targets, whitespace checks, production build, dependency audit and portable packaging passed. The packaged app was exercised end to end: the idle eye and four-option tray rendered correctly, Voice began listening immediately, Pause cancelled recording, Text produced a two-line quick take, and Full analysis then opened only the relevant Health expert.

## 18 July 2026: AllSeeingEye identity and repository documentation

- Renamed every user-visible product, prompt, package, executable and current-documentation reference to the exact product name **AllSeeingEye**.
- Changed the Windows application identity to `com.shabalalawatp.allseeingeye` and the portable artefact to `AllSeeingEye-<version>-portable.exe`. Private preload bridge names and developer-only smoke variables remain stable for compatibility.
- Replaced the legacy README with a current product manual covering the quick-first workflow, full expert architecture, twelve agents, knowledge-pack boundaries, setup, usage, privacy, security, testing, packaging, limitations and third-party terms.
- Captured four screenshots from the packaged AllSeeingEye build for the input tray, immediate voice recording, concise quick take and relevant-only full analysis. Desktop-preview imagery was deliberately excluded to avoid publishing unrelated screen content.
- Added Windows CI, CodeQL, pull-request dependency review, weekly Dependabot updates, hardened secret-file ignores and a root MIT licence for original project code while retaining the vendored component's separate terms.
- Publication verification: the configured-model preflight passed, 110 deterministic tests passed with one credential-dependent live test skipped, both TypeScript targets and the production build passed, the production dependency audit found zero vulnerabilities, the tracked credential scan passed, and the renamed portable package was exercised for the documented screenshot journeys.
