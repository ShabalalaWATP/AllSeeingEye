# KAN-81 panel body construction, 6 October 2026

Catalogue and traffic panel definitions now supply optional body factories.
GlobeControls resolves only the selected body's current factory, avoiding JSX
construction for closed catalogue and traffic panels on each live update.
Metadata, counts, callbacks and hooks still refresh normally. The selected body
continues to resolve when collapsed or while the chooser is visible, preserving
its existing state and lifecycle. Direct ControlPanel rendering supports both
ordinary React children and factories.

There is no body cache, new global state, permission change or altered stream
protocol. The canonical benchmark, synthetic fixture, dependencies and bundle
limits remain unchanged. Existing unknown-panel, removal, focus, selection,
correction and expiry behaviour is preserved.

The original implementation failed two intended body-construction regressions.
The final eight-file patch passes 37 distinct tests across 12 files, including
nine new cases. Scoped ESLint and Prettier, both full TypeScript configurations,
production build and existing bundle budgets pass. Initial/globe gzip sizes are
202,546/806,879 bytes against limits of 245,760/870,400. Every touched source file
is below 350 lines. Independent quality and security reviews cleared the final
production changes and both narrow test repairs.

The first candidate passed 34 tests and failed two new expectations: the existing
News panel intentionally has two regions, and dashboard selection requires the
real view owner. Those assertions were corrected without changing production
files or weakening freshness/access checks. The first full app type check also
caught an existing corridor test passing the new function-or-node union straight
to Children.toArray. That test now resolves the factory before its unchanged
assertions. All original failures and final owned-process cleanup receipts are
retained in the private lazy-panel-bodies/evidence/v1 packet.

Root applied the exact reviewed patch to PR 130's clean 4e637dcf base and verified
all eight source hashes and four protected input hashes. Patch SHA-256:
024ca02212e695ded6854b3b4823916ddf153bf8435627be4646c06bb98e6e67.
Evidence result SHA-256:
a72ac55f22ecb24c32963bb206d55222a266547cde9e5b25daf8f6a829677334.

No timing or coverage result was measured for this subsequent patch. PR 130's
earlier head passed all 38 reported checks, with 4,587 frontend tests passing and
one skip, but that CI does not validate these new files. The previously recorded
canonical v4 candidate still misses the original median/maximum targets. KAN-81
remains open pending new published-head CI, measured latency and real-browser
validation.
