# External media privacy controls

KAN-184 controls when the browser connects to TradingView, YouTube and IPCamLive.
Without a remembered provider choice, the app renders local explanatory text, a
privacy-policy link and a descriptive Load button. It creates no provider iframe,
script, image or preconnect before that action. Links contact the provider only if
the reader follows them.

TradingView receives the selected public symbol, browser details and IP address.
Camera embed providers receive the chosen video or camera, browser details and IP
address. Embeds may set cookies. The app does not send account credentials, report
content or research questions to these frames. YouTube catalogue addresses are
validated and rewritten to `www.youtube-nocookie.com` before rendering; regular
`www.youtube.com` remains a permitted catalogue input but is absent from the
production `frame-src` policy. IPCamLive retains its approved player destination.
The existing sandbox and referrer policies remain provider-specific.

Camera selection still requires an explicit load or Play action. Remembering
YouTube or IPCamLive never starts a newly selected camera. Stop and hidden-tab
suspension release the current player; Stop does not erase a remembered choice.
Direct camera images, HLS, MP4 and MJPEG use their existing Load image or Play video
gates. Direct requests also reveal the reader's IP address and browser details to
the provider. Same-origin image relays instead contact the provider from the
server. These controls do not inspect or establish each provider's cookie behaviour.

## Choices and withdrawal

- Load alone permits the current mounted widget. Leaving it removes that grant.
- “Remember for [provider] until I reload or sign out” is unchecked and stores the
  choice only in application memory. It survives component navigation, but resets
  on reload, sign-out, inactive-account transition or account change.
- “Also save this choice in this browser, including for other accounts” is a
  separate unchecked checkbox, shown only after selecting Remember. Only that
  explicit opt-in writes a browser preference. It applies to every account using
  the same browser profile and origin.
- Forget beside an embed, or Settings → External media, unmounts open embeds from
  that provider and removes the remembered choice. Saved-choice withdrawal is
  synchronised to other open tabs through storage events. It cannot undo data
  already transmitted or remove provider-owned cookies.
- Invalid saved values do not grant permission. If browser storage fails, the
  interface explains that saving fell back to session memory, or that a saved
  choice could not be removed. In the latter case it blocks current media and
  retains that block across account changes and storage updates. It tells the
  reader to clear site data before reopening the app.

## Storage declaration for KAN-165

The forthcoming public privacy/storage page must include this entry. This document
records the technical implementation; it is not approved controller/legal wording.

| Field | Value |
| --- | --- |
| Key | `ase.embed-consent.v1` |
| Mechanism | Same-origin `localStorage`; no server write or consent cookie |
| Purpose | Remember explicitly selected external media providers in this browser |
| Written when | The reader checks both Remember and the separate browser-storage option, then loads the content |
| Contents | `{"version":1,"providers":["tradingview","youtube","ipcamlive"]}`; only chosen provider IDs are stored |
| Personal identifiers | None in this value; provider IDs only |
| Retention | Until the reader forgets the provider or clears site data; no automatic expiry |
| Withdrawal | Beside the embed or Settings → External media; removing the last provider deletes the key |
| Default | No key; one-widget or session choices stay in memory |

Provider privacy links: [TradingView](https://www.tradingview.com/privacy-policy/),
[YouTube / Google](https://policies.google.com/privacy),
[IPCamLive](https://www.ipcamlive.com/privacy).

The original ticket's assertion that these gates remove any need for a banner is
not established by this implementation. Legal requirements, controller wording
and other application storage remain part of KAN-165/KAN-183 review.

## Isolated browser verification

`frontend/scripts/embed-consent.html` is a Vite development-only entry for the real
`MarketWorkspace`, `CameraStream` and privacy settings components with local fixture
data. It uses a synthetic in-memory identity, makes no API calls and is not an entry
in the production build. Do not open it without browser request interception.

1. Start the private worktree's Vite server on an unused loopback port with
   `pnpm exec vite --host 127.0.0.1 --port 5484 --strictPort`.
2. Open `about:blank` in a fresh named Playwright CLI session. Before navigation,
   install a context route for `**/*`: continue only this exact loopback origin
   (excluding `/api/`), fulfil the three expected provider hosts with local HTML,
   and abort every other destination. Record attempted provider URLs and the
   current interaction phase. No real provider response is needed.
3. Navigate to `/scripts/embed-consent.html`. Assert no provider attempts, iframe
   or local-storage key. Capture the placeholder state and run accessibility
   checks, including contrast in the real browser.
4. Load each provider individually. Assert one corresponding frame request after
   each action, with YouTube using only the nocookie host. Check memory remembering,
   new camera selection still waiting for Play, Stop, withdrawal and reload.
5. Check both remember boxes explicitly, load, reload, verify the saved provider
   is restored, then withdraw and reload again. Check 360-pixel layout and keyboard
   operation. Keep logs/screenshots under ignored `output/playwright/kan-184/`.
6. Close only this named browser session and stop only its Vite process.

This fixture verifies request admission and UI behaviour. Intercepted responses
cannot establish real provider playback, downstream requests, cookies, availability
or production Caddy deployment behaviour. The separate Caddy policy test verifies
the committed frame-host contract.
