# Final browser acceptance evidence

Captured 10 October 2026. Screenshots and sanitised logs are retained as review
evidence, not application assets. All identities and form data were synthetic.
No provider traffic, real enquiry, email or production mutation was sent.

## KAN-168 and KAN-172 public pages

The production build at `ca810947` ran against a private loopback fixture serving
public flags and a fixed enquiry receipt. Chromium 155.0.8059.39, Node 24.19.0,
fresh named browser context, off-origin HTTP and all WebSockets blocked.

The desktop capture uses 1,440 CSS pixels. The complete contact-section capture
uses a 390-pixel width and a taller 1,900-pixel viewport so the fixed header does
not obscure fields in the stitched element capture. Interaction and overflow
checks use 390 by 844. Finite screenshot animations were finished by Playwright;
this evidence is not a performance measurement.

- [Desktop contact section](assets/KAN-216-final/contact-desktop.png)
- [Complete 390-pixel contact section](assets/KAN-216-final/contact-mobile.png)
- [Synthetic successful submission](assets/KAN-216-final/contact-success-mobile.png)
- [390-pixel footer](assets/KAN-216-final/footer-mobile.png)
- [Business page](assets/KAN-216-final/business-mobile.png)

Both complete form captures show the heading, every user-facing field, privacy
acknowledgement and submit button. A valid synthetic submission produced the
receipt and removed the form. No horizontal overflow was observed at 390 pixels.

All three new routes rendered their titles, draft warnings and `noindex, follow`
metadata at 390 by 844 without horizontal overflow. Initial document loads retain
the browser's focus, as designed; following the Terms page's Business details
link moved focus to the new H1. [Route observations](assets/KAN-216-final/public-policy-browser.json)
record initial-load results separately from this client-side navigation check.

## KAN-169 administrator contrast

The same isolated production fixture supplied 26 synthetic enquiries, including
long unbroken values and literal HTML text. The 1,280 by 900 obsidian view was
checked with axe 4.13.0 after fonts loaded. There were no unexpected requests.

- [Default view](assets/KAN-216-final/admin-desktop.png)
- [Delete confirmation](assets/KAN-216-final/admin-delete.png)
- [Final-build axe results](assets/KAN-216-final/admin-axe-final.json)
- [Expanded-message results](assets/KAN-216-final/admin-axe-expanded.json)
- [Confirmation results](assets/KAN-216-final/admin-axe-dialog.json)

Default and expanded states had zero violations, with four colour-contrast nodes
requiring manual review because axe cannot resolve the decorative gradient.
The confirmation had zero violations and no incomplete checks. An initial helper
waited for `dialog`; the actual accessible role is `alertdialog`. A fresh snapshot
confirmed that role before the successful check. No product change was needed.

Browser-computed values were captured for each unresolved node and every ancestor.
The grid consists of two 18% `rgb(42,42,54)` lines over `rgb(7,7,11)`, with normal
blending, opacity one and no filters. Taking both grid lines at their intersection
and a fully opaque mask gives the conservative brightest background
`rgb(18.466,18.466,25.0868)`. Fading the actual mask only darkens it.

| Node | Actual foreground | Worst-case ratio | Required ratio |
| --- | --- | ---: | ---: |
| Access and teams eyebrow, 11 px | `rgb(255,111,55)` | 6.71 | 4.5 |
| Enquiries H1, 30 px | `rgb(233,228,220)` | 14.68 | 3.0 |
| Description, 14 px | `rgb(154,149,163)` | 6.37 | 4.5 |
| Enquiry status label, 14 px | `rgb(233,228,220)` | 14.68 | 4.5 |

[Calculated resolution](assets/KAN-216-final/admin-contrast-resolution.json)
uses WCAG relative luminance and the observed opacity/font values. All four pass.
This resolves those specific incomplete checks, not a whole-product conformance
audit. Default/final checks span the pre-footer and `ca810947` builds; their
administrator implementation is unchanged and the final-build nodes agree.

## KAN-184 embed consent

[The separate capture](assets/KAN-184-final/EVIDENCE.md) records 17 successful
state observations at `4c9327a9`, whose consent implementation is unchanged in
`ca810947`. Eight explicitly admitted frame requests were fulfilled with inert
local HTML: TradingView three, nocookie YouTube four and IPCamLive one.
There were zero API or unexpected HTTP attempts and zero forwarded provider
requests. The committed component fixture covers consent, withdrawal, reload,
memory and explicit browser persistence, camera Play/Stop and 360-pixel keyboard
operation. Its limits and initial scripted-click observation remain explicit.

The [compact request ledger](assets/KAN-184-final/provider-attempts.json) and
[complete sanitised capture](assets/KAN-184-final/network-capture.json) omit query
strings, fragments, headers, cookies, bodies and storage values. This verifies
component request admission, not real provider playback or deployed Caddy.
