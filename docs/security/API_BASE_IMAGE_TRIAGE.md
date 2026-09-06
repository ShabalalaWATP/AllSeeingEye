# API base image vulnerability triage

Reviewed 6 September 2026 against the immutable images below. Both builds and
the CI-equivalent vulnerability gates passed. **The API still has 54 unfixed
HIGH/CRITICAL package findings: 51 HIGH and 3 CRITICAL, covering 18 unique CVEs
across 19 installed Debian packages.** The web image has zero HIGH/CRITICAL
findings including unfixed issues. A fixable-only pass does not establish that
the API is free of serious vulnerabilities or ready for public exposure.

## Build and scan evidence

| Image                       | Immutable image ID                                                        | Build exit | Fixable HIGH/CRITICAL gate exit |
| --------------------------- | ------------------------------------------------------------------------- | ---------- | ------------------------------- |
| `ase-api:improvement-check` | `sha256:239c56279d9b3eaa7b5e61c8cb84685318d66b33e300b7399b490829a2c285a3` | 0          | 0                               |
| `ase-web:improvement-check` | `sha256:05322b59e64dd2e1d279e6f10edbee1d12624b8c82d9e81bf3172ddf858f7f5f` | 0          | 0                               |

Actual build commands, run from `backend` and the repository root respectively:

```powershell
docker build --progress plain --iidfile ../data/improvement-container-qa/api-image-id.txt -t ase-api:improvement-check .
docker build --progress plain --iidfile data/improvement-container-qa/web-image-id.txt -t ase-web:improvement-check -f frontend/Dockerfile .
```

Trivy 0.68.2 ran from scanner image
`sha256:05d0126976bdedcd0782a0336f77832dbea1c81b9cc5e4b3a5ea5d2ec863aca7`.
The cached database was updated `2026-09-05T19:14:02Z`, downloaded
`2026-09-05T23:24:01Z`, with next update `2026-09-06T19:14:02Z`.
The invocation below was run for each exact image ID, with the corresponding
`trivy-api.json` or `trivy-web.json` output name:

```powershell
$scannerImage = 'sha256:05d0126976bdedcd0782a0336f77832dbea1c81b9cc5e4b3a5ea5d2ec863aca7'
$targetImage = 'sha256:239c56279d9b3eaa7b5e61c8cb84685318d66b33e300b7399b490829a2c285a3'
docker run --rm --network none --volume /var/run/docker.sock:/var/run/docker.sock --mount type=bind,source=C:/AlexDev/OSINT/data/trivy-cache,target=/root/.cache/trivy --mount type=bind,source=C:/AlexDev/OSINT/data/improvement-container-qa,target=/results $scannerImage image --quiet --skip-db-update --offline-scan --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 --format json --output /results/trivy-api.json $targetImage
```

The informational inventories used the same invocation with `--ignore-unfixed`
omitted, `--exit-code 0`, and output names `trivy-*-including-unfixed.json`.
Their exit status is therefore informational, not a vulnerability gate. Both
inventory commands exited 0. All 54 API matches are in the Debian 13.6 OS target;
there were no HIGH/CRITICAL matches in the Python, uv or uvx scan targets.

The API was rebuilt after the final audit enum correction and final source line-ending normalisation. Its 302 copied
source/metadata files matched the working tree by SHA-256 with zero differences:
`src/**`, `alembic/**`, `pyproject.toml`, `uv.lock`, `README.md`, `alembic.ini`.
The comparison excludes bytecode and caches. Tests and the main documentation
tree are not copied into the API runtime image and were outside this comparison.
The web build began after the frontend source owner released production edits;
no equivalent source-file hash comparison is claimed for its compiled bundle.

Local, ignored evidence is under `data/improvement-container-qa`: build logs,
immutable ID files, four final Trivy JSON reports, both API source manifests,
`api-runtime-inspection.txt`, `inspect-runtime.sh`, and `api-triage.json`.
Files labelled `initial` are superseded and are not the final API evidence.

## Installed components and reachability

Read-only inspection used the exact API image with `--network none --read-only`,
a disposable `/tmp` tmpfs, and no application service start. Package removals
were **simulations only**. No exploit payloads were run. Image inspection reports
`amd64`, `USER ase`; the Dockerfile creates that user with UID 10001. The checked-in
Compose API configuration uses a read-only root filesystem and
`no-new-privileges:true`. It has an unconfigured `/etc/fstab`. These are declared
deployment controls, not verification of an existing operator deployment.

The Debian tracker explicitly describes its matches at **source package** level.
An installed binary package from that source does not prove that every affected
module or executable is present. Conversely, an absent application call path
does not remove vulnerable code from the image.

| CVE and scanner severity                                                                                                                                                                                                                                     | Installed evidence and scoped conclusion                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [CVE-2026-42496](https://security-tracker.debian.org/tracker/CVE-2026-42496), CRITICAL; [CVE-2026-42497](https://security-tracker.debian.org/tracker/CVE-2026-42497), HIGH; [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538), HIGH | All match `perl-base` 5.40.1-6, but `Archive/Tar.pm` is absent from `/usr` and `/app`. The affected Perl archive extraction component is absent from this image. These are not findings against Python archive handling. Reassess if Perl archive modules are added.                                                                                                                                                                                                                                                                    |
| [CVE-2026-48962](https://security-tracker.debian.org/tracker/CVE-2026-48962), HIGH; [CVE-2026-57433](https://security-tracker.debian.org/tracker/CVE-2026-57433), HIGH                                                                                       | `File/GlobMapper.pm` and `Storable.pm` are absent. The reported output-glob evaluation and Storable deserialisation components are absent, despite matching the Perl source package.                                                                                                                                                                                                                                                                                                                                                    |
| [CVE-2026-8376](https://security-tracker.debian.org/tracker/CVE-2026-8376), CRITICAL                                                                                                                                                                         | `/usr/bin/perl` exists, but reports `x86_64-linux-gnu-thread-multi`, `ivsize=8`, `ptrsize=8`. The advisory's 32-bit build prerequisite does not match this exact image. This conclusion must not be copied to a 32-bit build.                                                                                                                                                                                                                                                                                                           |
| [CVE-2026-13221](https://lists.security.metacpan.org/cve-announce/msg/41780104/), CRITICAL; [CVE-2026-57432](https://security-tracker.debian.org/tracker/CVE-2026-57432), HIGH                                                                               | Perl 5.40.1 is present at `/usr/bin/perl`. The former needs a huge fixed-string regex alternation affecting a decision; the latter needs an untrusted pack/unpack template. No application Perl invocation was found. The affected interpreter remains installed, so these remain review items rather than a claim of remediated code.                                                                                                                                                                                                  |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742), HIGH, 2 package matches                                                                                                                                                        | `libsystemd0` and `libudev1` 257.13-1~deb13u1 are present as `/usr/lib/x86_64-linux-gnu/libsystemd.so.0.40.0` and `libudev.so.1.7.10`. The affected `systemd-homed` executable is absent. The advisory requires a logged-in homed-managed user; the libraries alone do not provide this service.                                                                                                                                                                                                                                        |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720), HIGH, 4 package matches                                                                                                                                                        | ncurses 6.5+20250216-2 includes affected `/usr/bin/infocmp`. The advisory concerns this CLI's `analyze_string`, not every ncurses library function. Python readline links `libtinfo.so.6`, but no application `infocmp` invocation was found. Retain as an installed-tool review item.                                                                                                                                                                                                                                                  |
| [CVE-2026-41992](https://security-tracker.debian.org/tracker/CVE-2026-41992), HIGH                                                                                                                                                                           | `/usr/bin/gzip` 1.13-1 is present. The trigger requires crafted LZW followed by LZH input within one GNU gzip invocation. No application GNU gzip subprocess was found. This does not establish exploitation through ordinary Python HTTP decompression.                                                                                                                                                                                                                                                                                |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369), HIGH                                                                                                                                                                           | `/usr/lib/x86_64-linux-gnu/libacl.so.1.1.2302` is installed. The advisory needs a privileged pathname-based ACL caller and attacker-controlled path components. No such application call was found; the API runs as UID 10001. Privileged maintenance or a changed deployment needs separate review.                                                                                                                                                                                                                                    |
| [CVE-2026-11822](https://security-tracker.debian.org/tracker/CVE-2026-11822) and [CVE-2026-11824](https://security-tracker.debian.org/tracker/CVE-2026-11824), HIGH                                                                                          | `libsqlite3-0` 3.46.1-7+deb13u1 is genuinely used: Python `_sqlite3.cpython-313-x86_64-linux-gnu.so` links `/lib/x86_64-linux-gnu/libsqlite3.so.0`, resolving to `libsqlite3.so.0.8.6`. SQLite reports 3.46.1 with `ENABLE_FTS5`. The advisories require a malicious database and FTS5 MATCH processing. No FTS5 schema/query was found in application sources or migrations. The checked-in production Compose uses PostgreSQL; SQLite remains supported locally. Keep these as priority review items because affected code is linked. |

The four util-linux CVEs below each match nine installed binary packages, making
36 package findings. Those packages are `bsdutils`, `libblkid1`, `liblastlog2-2`,
`libmount1`, `libsmartcols1`, `libuuid1`, `login`, `mount`, and `util-linux`, derived
from util-linux 2.41.5-0+deb13u1 (with Debian epoch/version wrappers for bsdutils
and login). The relevant installed paths are `/usr/bin/mount`,
`/usr/bin/nsenter`, and `/usr/lib/x86_64-linux-gnu/libmount.so.1.1.0`.

| CVE, all HIGH                                                                | Required path and deployment limit                                                                                                                                                      |
| ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) | Failed mount helper followed by privileged X-mount post-hooks. No application mount helper invocation was found.                                                                        |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) | Privileged operator uses `nsenter --join-cgroup` against an attacker-controlled target. This is not an API operation.                                                                   |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) | Linux 6.15+ detached-tree mount and an authorised `X-mount.subdir` fstab entry. The image has no such fstab entries. Host-kernel and altered deployment prerequisites were not tested.  |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | Restricted SUID bind mount with attacker-replaceable source and X-mount ownership/mode options. The declared non-root/no-new-privileges deployment and empty fstab constrain this path. |

These are retained as review items for deployment and maintenance changes, not
declared fixed. Source searches covered `backend/src` and `backend/alembic` for
Perl, subprocess/shell execution, GNU gzip, FTS5/MATCH, nsenter and the named ACL
API. Python regex variable names and HTTP `If-None-Match` were unrelated hits.
The persistence factory in `backend/src/ase/adapters/persistence/session.py`
supports SQLite explicitly; report search stores JSON vectors in
`backend/src/ase/adapters/persistence/report_search.py`. No complete hostile
request-to-affected-sink path was established. This is bounded triage, not proof
against all transitive dependency behaviour or future features.

## Removal assessment and release follow-up

`dpkg-query` marks `perl-base`, `gzip`, `ncurses-bin`, `ncurses-base`, `bsdutils`
and `util-linux` Essential. `apt-get --simulate purge` explicitly warns against
removing the first three. Removing `libacl1` breaks coreutils/sed/tar dependencies;
removing `libsqlite3-0` breaks util-linux's liblastlog dependency as well as
Python SQLite. Removing `libsystemd0` or `libudev1` also breaks Essential package
dependencies. Python readline uses libtinfo and `_uuid` uses libuuid. Forced
Essential removals, deleting library files, or swapping distribution families
solely to reduce scanner counts are not supported by this evidence.

The only bounded candidate examined was removing the non-Essential `mount`
package: its simulation removes only that package. This would remove an unused
CLI and four package matches, but **would leave libmount, nsenter and 32 other
util-linux matches**. It would not clear a unique CVE or the API's critical
findings. It is an optional follow-up requiring a rebuilt image, startup/health,
migration and backup/restore checks; no removal or Dockerfile edit was made.

Before release or broader exposure:

1. Rebuild from a refreshed supported Python/Debian base and rescan with a fresh
   database. Keep both the fixable gate and the full unfixed inventory.
2. Track the linked SQLite fixes first, followed by installed interpreter/tool
   findings. Debian currently records several as `no-dsa` or postponed for
   stable, despite fixes in unstable/upstream. An upstream version number does
   not establish that a supported stable package is available.
3. Resolve findings through supported updates, or record an owner-approved,
   time-bounded exception tied to the image ID and deployment assumptions.
   This document is evidence for that decision, not approval or suppression.
4. Reassess immediately if untrusted database import/FTS5, Perl processing,
   privileged maintenance, mount helpers, added Perl modules, a different image
   architecture or public exposure is introduced. Preserve non-root execution,
   read-only root filesystem and no-new-privileges.

No operator containers, data, credentials or deployment configuration were
changed during verification. No vulnerability ignores were added.
