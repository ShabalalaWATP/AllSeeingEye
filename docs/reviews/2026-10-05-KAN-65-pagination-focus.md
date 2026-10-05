# KAN-65 pagination focus repair

## Observed behaviour

On 5 October 2026, manual keyboard checks against released `91d2034d` in Edge
confirmed that the globe and flat map rendered, the page heading followed the
selected view, and the direct loaded-event link focused the labelled search.
Search, no-match reset, event inspection and closing the panel remained usable.
Closing the event inspector returned focus to the originating record; Escape
from the list returned focus to its entry link.

With 39 loaded natural-hazard records over two pages, activating Next with
Return advanced to the final page and disabled the focused control. The browser
accessibility observation then reported focus on the web area. Source review
confirmed that pagination used native disabled controls without focus management.

The repair keeps boundary controls focusable, exposes their unavailable
state with `aria-disabled`, and ignores activation at a boundary. A valid page
change retains the existing settled-result announcement. Repeated activation at
a boundary must not change the page or request another announcement.

## Scope and validation

The repair is isolated from KAN-81 performance work and the primary checkout.
Regression tests must cover both boundaries, repeated Return/Space activation,
Tab navigation, and the existing settled/background-update behaviour. Required
checks and independent review results are recorded below.

- Both new Return/Space regression cases failed against the unchanged product
  because the final-page Next button was natively disabled. An earlier timer
  harness timeout is preserved separately and is not product failure evidence.
- The corrected regressions pass with the repair. The combined pagination,
  geographic-precision and direct-list-entry checks pass: 15 tests across three
  files. A fixture label selector was corrected before the final passing run;
  the product repair remained unchanged.
- Independent quality and security reviews are clear. Reviewed product SHA-256:
  `490ad1455ce7e6aebb3d2c7e762db2d69eaf8698ce8e7cc514e6f20c98c77a0c`.
  Final regression-test SHA-256:
  `48e28ef6689db59695d8f94858802f4d9807e7145e07be2ba67d9db5e39cee0b`.
- App and Node TypeScript checks, targeted ESLint and Prettier, production build,
  bundle budgets, file-length check and `git diff --check` pass. Compiled CSS
  contains the unavailable opacity, cursor and hover rules. The product has 233
  lines and the regression test 78 lines. The file-length check reports only
  existing warnings in untouched files.
- Bundle sizes remain within their existing limits: initial JavaScript 202,535
  of 245,760 gzip bytes and additional globe JavaScript 807,027 of 870,400 bytes.
- Coverage has not been measured for this focused run. No access, network or
  migration behaviour changes in this repair.

Manual screen-reader verification remains outstanding. The production Edge
observations establish visual and keyboard behaviour only; no NVDA speech was
observed and KAN-65 has not been declared complete.
