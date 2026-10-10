# KAN-232 migration startup prerequisite

The shared session branch at `8cb571c7` also exceeded the existing migration
startup budget: its isolated startup tests reported 201 project imports, with
one failure and one pass in 9.38 seconds. This precedes the enquiry and consumed
alert evidence additions that raised the integrated branch to 204 imports.

The four backend source/test files from the independently reviewed repair
`9ea7b556` are applied unchanged. Infrastructure dataset adapters load only when
their CLI command runs. All five commands retain their options, contact default,
arguments, count output and sanitised failures. The fewer-than-200 import budget
and no-application-wiring/feed/LLM checks are unchanged. The startup regression
also explicitly excludes the three infrastructure importer modules.

Validation on this prerequisite branch:

- Fresh in-memory migration: 193 project imports, with no deferred infrastructure
  importers loaded.
- Startup, dispatcher and infrastructure regression group: 22 tests passed in
  9.27 seconds.
- Ruff, formatting, scoped mypy, scoped Bandit and `git diff --check` passed.
- Source/test files are identical to the reviewed repair and remain below 350
  lines. No migration, dependency, generated contract or frontend file changed.

```text
uv run --frozen --offline pytest tests/test_startup_imports.py tests/test_cli_infrastructure_dispatch.py tests/test_infrastructure_import.py -q --no-cov
```

Tests used isolated temporary or in-memory SQLite with shared database environment
variables cleared. No external provider, production service or shared database
was used. Coverage and the full suite were not rerun. The coordinator owns
publication and propagation to the dependent branches.
