# KAN-70: historical synthetic secret-scan findings

The first manual CI campaign run,
[37003887806](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/37003887806),
failed its Gitleaks step. Gitleaks 8.24.3 scanned 935 commits and reported five
historical `generic-api-key` matches. The campaign stopped with **0 of 20
successful runs** and was not retried. This change does not convert that failed
campaign into acceptance evidence.

The completed static triage assessed all five matches as `not_actionable` with
high confidence: test-prefixed synthetic values in offline doubles or isolated
fixtures, including an evaluation marker with a reserved `.invalid` URL. No
production credential was identified. The exception scope is the exact historical
commit, path, rule and line below; no credential strings are reproduced here.

| Historical commit | Test path, relative to `backend/tests/` | Line |
| --- | --- | --- |
| `045685b8019a5a5669d8703dc546c355792a2526` | `evaluation_run_helpers.py` | 20 |
| `41464aae4cd5aa6a8c3faaede4fba2cb383d202e` | `test_source_assets.py` | 31 |
| `2b599d0af53d3f3a08a668722e57b5b09f140d5a` | `test_acled_credentials.py` | 102 |
| `d6b95602ef1a19a33b4630cd20bb35fa3799ffdd` | `test_map_feed_registration.py` | 25 |
| `64645b1728032cb01e6136f061d6f412d00e23d7` | `test_firms_feed.py` | 17 |

Only these five fingerprints are added to [`.gitleaksignore`](../../.gitleaksignore).
The two KAN-31 entries remain unchanged. No test literal, history, rule, workflow,
coverage threshold or required check is changed. In particular, the
[security job](../../.github/workflows/ci.yml) retains `fetch-depth: 0` and its
pinned Gitleaks action. Other occurrences remain eligible for detection.

## Validation

The local before/after check passed on 2 October 2026. A new public, credential-free
clone was checked out at `13e9525d904e744e0bc7ea329e8d475234f86f25`. Its remote
configuration was removed while retaining every fetched remote-tracking ref and
tag. The frozen refs contained 1,103 reachable commits; Gitleaks reported 938
scanned commits in each run. These are current local counts, not the failed
action's historical count of 935. The default `git log -p -U0 --full-history --all`
scope was preserved, including historical branches outside main's ancestry.

Both runs used Gitleaks `v8.24.3`, its built-in rules and the action's flags:

```text
gitleaks detect --redact -v --exit-code=2 --report-format=sarif \
  --report-path=/out/results.sarif --log-level=debug
```

| Frozen history | Exit | SARIF findings | Result |
| --- | --- | --- | --- |
| Original two KAN-31 exceptions | 2 | 5 | Exact set of five triaged fingerprints |
| Original two plus five KAN-70 exceptions | 0 | 0 | No findings |

Only the ignore-file contents differed between scans. The original file was
restored afterwards, and both refs and the otherwise clean private checkout were
verified. The exact set check also confirmed two existing plus five triaged
entries, with no extra exception. Local document links and `git diff --check`
passed. No application tests or coverage measurement were needed for these two
configuration/documentation files.

The official scanner image was pinned to
`sha256:e1b35e12a8c6fa8901f060459cfb6b2fc4c484d3afbe3b029733a3bbfab07055`.
Each disposable container had networking disabled, a read-only source/root
filesystem, no published port or Docker socket, a private report mount and no
forwarded host credentials. The effective environment matched the pinned image
defaults plus declared fixture variables. Bounded commands and exact
UUID-label/container-ID cleanup left no
owned containers, cleanup errors or unresolved operations.

An initial local harness attempt rejected the official version string's `v`
prefix after completing its baseline scan. Its report and clean cleanup evidence
were retained. Independent review cleared the exact version-string correction;
the complete before/after pair above then ran under a fresh single-use claim.
This was a local harness correction, not a retry of the failed CI campaign.

Independent read-only reviews cleared the five-entry patch and the private
launcher, including the narrow version correction. Redacted SARIF, command logs,
frozen refs and cleanup evidence are retained privately under
`codex-kan70-gitleaks-16e256421a8645e0a5c24228cb7f12bf`:

- `result.json` and `cleanup.json`: paired results and empty final resource census.
- `before-rechecked/results.sarif`, SHA-256
  `629f46d74912f63fc46cef78efec271ae52cd9254901098e79d284a09531e593`.
- `after/results.sarif`, SHA-256
  `f1cc1fc5bf34d5e9643655ac6480ff4681e27aa9c2c639f03067fc7ea8595e3d`.
- Frozen normalised refs, SHA-256
  `79e45d5387149e4b3956d6e9834686a24b9406a815c12196574507cbfb456e4f`.

Fresh PR CI and a separately authorised fresh 20-run campaign are still required.
This draft does not authorise merging, deployment or credential rotation.
