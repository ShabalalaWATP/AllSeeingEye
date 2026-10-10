# KAN-184 external-media consent browser evidence

Captured on 10 October 2026 against source commit
`4c9327a9da2697e7c1f63b4f6dda9373148aa9bb` in
`C:\Users\alexo\.codex\worktrees\kan-172-public-page-acceptance\OSINT`.
No tracked source files were changed and no commit was created.

## Scope and isolation

This is a real Chromium browser capture of the committed development-only
`/scripts/embed-consent.html` component fixture. It mounts the actual
`ClickToLoadEmbed`, `MarketWorkspace`, `CameraStream` and
`EmbedPrivacyPreferences` components with synthetic in-memory identity. It is
not a production-route or deployed-site test.

Playwright CLI used a fresh isolated session named `kan184-final`, Chromium
`155.0.8059.39`, Node `24.19.0` and the existing frozen frontend dependencies.
The private Vite server bound only `127.0.0.1:5494`. Before navigation, a browser
context route allowed only assets at that exact loopback origin, excluding
`/api/`. Exact expected provider frame requests received inert locally supplied
HTML. Every other destination was aborted. Service workers were blocked and
all WebSockets were closed. No provider request was forwarded and no live API,
credentials or notification service was used.

## Observed results

The JSON capture contains 17 successful state observations:

- Before consent: no provider attempt, no iframe, no external script/image/media
  resource or preconnect, no saved preference, and all Remember boxes unchecked.
- Explicit Load admitted each provider separately. The YouTube frame used only
  `www.youtube-nocookie.com`.
- Block removed all three open frames. Reload after withdrawal attempted no
  provider request.
- Remembering YouTube in memory wrote no browser preference. Selecting another
  camera removed the frame and waited for Play. Play admitted the frame; Stop
  removed it. Reload reset memory-only consent.
- Explicitly checking both Remember and browser-storage options, then loading
  TradingView, saved the preference. Reload admitted the remembered chart.
  Withdrawal through the privacy settings removed the frame and saved key.
  The following reload attempted no provider request.
- At 360 CSS pixels, keyboard Enter activated Load and Block. Withdrawal returned
  focus to Load. No horizontal overflow was observed.

| Request origin | Path | Attempts | Handling |
| --- | --- | ---: | --- |
| `https://www.tradingview-widget.com` | `/embed-widget/advanced-chart/` | 3 | Local HTML fulfilment only |
| `https://www.youtube-nocookie.com` | `/embed/UemFRPrl1hk` | 4 | Local HTML fulfilment only |
| `https://ipcamlive.com` | `/player/player.php` | 1 | Local HTML fulfilment only |
| `http://127.0.0.1:5494` | Local fixture, modules, styles and fonts | 305 | Exact-origin asset requests |
| `ws://127.0.0.1:5494` | `/` | 10 | Closed locally, Vite HMR blocked |

API attempts: **0**. Unexpected HTTP destinations: **0**. Provider requests
forwarded: **0**. Query strings and fragments are deliberately excluded from the
capture, as are headers, cookies, request/response bodies and storage values.
The capture records only whether the preference key exists.

## Harness observation and limits

The first combined script stopped at saved-choice settings withdrawal because
the clicked state remained unchanged. A fresh DOM snapshot and explicit CLI
click on the observed settings-list button removed the frame and key. The final
reload and keyboard checks then passed. This initial harness observation is
retained in `network-capture.json`; no production defect was established and no
source correction was made. Block withdrawal on all three embeds had already
passed independently.

The browser console reported the expected Vite HMR errors caused by deliberately
blocking WebSockets. This capture does not establish real provider playback,
downstream requests, cookie behaviour, availability, legal compliance or deployed
Caddy policy. It is not a full accessibility audit or performance measurement.

## Reviewable files

- `network-capture.json`: complete sanitised request ledger and observations.
- `provider-attempts.json`: compact provider origin/path/phase ledger.
- `consent-observations.json`: concise sequence of the 17 successful checks.
- `01-before-consent.png`: all three local placeholders.
- `02-explicit-loads.png`: three frames containing only the inert local fixture.
- `03-withdrawn.png`: all embeds blocked after withdrawal.
- `04-new-camera-awaits-play.png`: remembered provider still requiring Play.
- `05-saved-choice-reload.png`: explicit browser choice restored after reload.
- `06-mobile-withdrawn.png`: 360-pixel layout and returned keyboard focus.

The interception and assertion scripts remain in the ignored local capture
directory named above. They are not part of this published evidence bundle,
application source or committed test files.
Raw HAR files, cookies and response bodies were not exported. The main JSON
records capture start/completion UTC times and the exact source commit.

Cleanup completed: the named browser session was closed, only the owned Vite
process was stopped, and port 5494 was verified to have no listener. Git status
remained clean at the source commit above. `SHA256SUMS.txt` records hashes for
the published evidence files.
