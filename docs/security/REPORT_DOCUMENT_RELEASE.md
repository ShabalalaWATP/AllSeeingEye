# Report document release checks

8 September 2026. PDF and DOCX exports now bind their output to the exact rendered
report version and validate current object access and the original request session
before returning private bytes.

The original route omitted a final session check. Four actual-render regressions
reproduced HTTP 200 after logout or token expiry. Adding that check exposed a
second gap: report deletion or membership removal could occur during the awaited
session validation. Two further regressions reproduced that object-access loss.

The final implementation uses a small application release service. It ends the
old renderer snapshot, takes the existing SQL administration guard, reloads actor,
membership, report and exact rendered version, and checks the current family plus
synchronous expiry. The request transaction remains open through response sending.
No lock spans rendering. Missing or mismatched exact version metadata refuses
release; filenames and the latest version are not used to infer that identity.

Twenty focused tests passed in 45.34 seconds, including eight release cases,
existing authenticated export API behaviour, HTML and PDF/DOCX compatibility.
Red/green logs remain locally in `data/document-object-release-red.log` and
`data/document-object-release-green.log`; the first session-only regressions are
also retained. Targeted mypy, Ruff, formatting and diff checks passed.

Independent read-only re-review found no blocking issue. It checked actual SQL
guard behaviour, fresh-row reads and the installed FastAPI request dependency
lifetime through response sending. No new lock primitive was introduced. A
separate PostgreSQL held-through-send case would strengthen concurrency evidence;
none was run specifically for this change. Logout uses a separate mutation path,
so the final family read is not claimed as an atomic database lock against logout.
No production system, real credential or external security target was used.
