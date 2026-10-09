# Self-hosting

The All Seeing Eye needs a persistent server: source polling, live events and research jobs run between browser visits. Use the repository's Docker Compose stack for a self-hosted installation. For Windows 11, macOS and Linux development, start with the [setup guide](SETUP.md).

This guide describes the application requirements. Keep your installation's addresses, administrator accounts, access keys and recovery locations in a private runbook.

## Requirements

- A Linux host with Docker Engine and the Compose plugin, Git and enough disk space for image builds, database growth and retained backups.
- Memory for the live event store, research workers and database. Monitor actual use when choosing capacity; the configured live-store budget does not cover the whole application.
- A domain with valid HTTPS, or a private network with a trusted local certificate.
- Outbound access to the source services and AI provider you enable.
- Protected storage for secrets and off-host backups.

The supplied stack contains PostgreSQL/PostGIS, the API, an isolated document parser and Caddy serving the frontend. Only the web service publishes ports. Keep the database and API private to the application network. Check the pinned container images support your host's architecture before using a different platform.

## Configure your installation

Clone the repository and select the revision you intend to run. From its root, copy `.env.example` to `.env`. Restrict access to that file and set the following values:

| Setting | What to supply |
| --- | --- |
| `ASE_ENV` | `prod` |
| `ASE_JWT_SECRET` | A unique random secret of at least 32 characters |
| `ASE_ENCRYPTION_KEY` | A different random secret of at least 32 characters |
| `POSTGRES_PASSWORD` | A unique random database password suitable for the Compose connection URL |
| `ASE_PUBLIC_BASE_URL` | The complete browser URL, for example `https://eye.example.org` |
| `ASE_SITE_ADDRESS` | The matching hostname, for example `eye.example.org` |
| `ASE_TLS` | A certificate contact email for a public domain, or `internal` for a local certificate authority |
| `ASE_HSTS_MAX_AGE` | Keep `0` until public HTTPS is confirmed |
| `ASE_FEEDS_CONTACT` | A project contact address or URL for upstream requests |

Compose supplies the database URL from the `POSTGRES_*` settings. Keep provider credentials server-side. AI connections are configured and tested through the app; a running server alone does not enable AI research.

Preserve `ASE_ENCRYPTION_KEY` separately from the database backup. It is needed to decrypt saved provider credentials and authenticator secrets. Replacing it does not re-encrypt existing data.

The API's `data/` bind mount must be writable by its non-root container user (UID/GID `10001`). For a new installation on Linux, create that directory with the appropriate ownership before starting. Keep the parser's network isolation, read-only filesystem and resource limits intact.

## Start and verify

Run from the repository root:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 api
docker compose exec api ase create-admin --email you@example.org --display-name "Your Name"
```

The API applies migrations on startup. The administrator command uses `ASE_ADMIN_PASSWORD` when that variable is set in the API container and prompts for a password only when it is not. Compose passes the root `.env` into the API container, so a value left there is used silently by every later `create-admin` and stays readable in the container's environment. Leave it unset to be prompted. If you set it for a one-off creation, remove it from `.env` afterwards and recreate the API container (`docker compose up -d api`), because a running container keeps the environment it started with. Sign in through the configured browser URL and enrol MFA. Authenticator apps work without SMTP; email codes require a configured mail relay.

Check both `/api/health` and `/api/ready` over HTTPS, load the interface and confirm that anonymous requests cannot open administration. Review source health in **Administration → Sources**. Upstream refusals, missing credentials and a source waiting for its next poll have different causes.

For public HTTPS, DNS must resolve to your host and the certificate challenge must be reachable. For internal certificates, establish trust on your own client devices. Enable a non-zero HSTS duration only after HTTPS works reliably; browsers retain that policy until it expires.

## Operation and updates

**Run one API process.** The live event store, rate limits and several coordination locks are process-local. Multiple API replicas or Uvicorn workers are not supported by this deployment design.

Keep time synchronisation enabled. Watch memory, disk capacity, source status, model usage and job failures. Compose bounds each service's container logs (json-file, five 20 MB files) and sets memory and process limits sized from the reference host; raise `mem_limit` in `docker-compose.yml` if a real workload needs more, since an API that reaches its limit is restarted and its live store warms up again. Arrange retention for any logs you ship elsewhere. The repository's `Uptime` workflow probes the reference deployment's site, health and readiness every 15 minutes and fails when the TLS certificate has under 14 days left, when `/` does not send `Strict-Transport-Security` with a `max-age` of at least a year, or when `security.txt` expires within 30 days; a failed run is the alert. Adapt its host for another installation. Schedule [encrypted backups](BACKUP_RESTORE.md#scheduled-encrypted-backups) on the host.

Caddy serves pre-compressed Brotli and gzip copies of the web client. Content-hashed files under `/assets/` are cached for a year as immutable; `index.html` and other fixed names revalidate on every visit, so a deploy reaches returning browsers immediately. A missing `/assets/` file answers 404 rather than the application shell.

The web image also serves `/robots.txt` (crawlers are asked to skip `/api/` and `/admin`) and an RFC 9116 `/.well-known/security.txt`; any other `/.well-known/` path answers 404. Both files live in `frontend/public`. The shipped `security.txt` names this project's reporting channel and the reference deployment's canonical address, so another installation should edit its `Contact` and `Canonical` lines. Renew its `Expires` date before it passes. The `Uptime` workflow fetches the live file and fails from 30 days before that date; it only warns while the live site serves no `Expires` line. Repository tests check the date's format but never fail CI because it has passed.

Before an update, review migration requirements, take and verify a backup, and check the target revision passed CI. An update restarts application processes: live feeds warm up again and running research may be interrupted. Verify health, readiness and sign-in after the update. Restoring application images does not reverse a database migration.

The repository also provides an [automatic deployment workflow](AUTOMATIC_DEPLOYMENT.md). Its controller is installation-specific and must be reviewed and adapted before use on another host.

### Database image

Compose builds the database from `infra/postgis/Dockerfile`: the digest-pinned upstream PostGIS image with Alpine security updates applied and the Go-built `gosu` replaced by Alpine's `su-exec`. Application updates never rebuild or restart it, so its system packages age until an operator refreshes it. Automatic deployment refuses changes under `infra/postgis/` until they are rolled out manually. Review a refresh when the base pin changes or the weekly `Database image` workflow turns red, and otherwise at least monthly.

**A security refresh requires `--pull --no-cache`.** Docker can reuse an unchanged
`RUN apk upgrade --no-cache` layer even when Alpine has released new packages.
The `apk` flag controls its package cache, not Docker's build cache. Docker's
`--no-cache` reruns build instructions; `--pull` checks the referenced base image.
Neither option changes a pinned digest. These are separate controls, as described
in Docker's [cache rules](https://docs.docker.com/build/cache/invalidation/),
[Compose build options](https://docs.docker.com/reference/cli/docker/compose/build/)
and [base-image pinning guidance](https://docs.docker.com/build/building/best-practices/#pin-base-image-versions).

The weekly workflow builds and scans a separate CI image. Its passing result does
not establish the contents of an older running image. Its vulnerability threshold
is fixable HIGH/CRITICAL findings. PostgreSQL and PostGIS in this image are built
from source under `/usr/local`; `apk upgrade` does not update those binaries.
Findings in them require a reviewed upstream pin change and compatibility checks.

#### Build and inspect the candidate

Use the intended reviewed revision and the installation's existing Compose project,
configuration and deployment lock. Obtain authorisation for the host build, reserve
disk and memory for it, and retain the previous image IDs and recovery material.
Build before the maintenance window where practical; this command does not replace
the running database:

```bash
set -e
docker compose build --pull --no-cache db
```

Confirm the package-update instruction executed instead of reporting `CACHED`.
Record the revision, build time, platform and successful build output. The supplied
Compose file has no image-name override, so its default tag is `<project>-db`.
Replace the example below with the actual tag reported by the build, including the
correct Compose project name. Run the following blocks in the same Bash session
and stop on any failed command:

```bash
set -e
db_tag='<project>-db'
db_image=$(docker image inspect --format '{{.Id}}' "$db_tag")
docker image inspect --format '{{.Id}} {{.Created}} {{.Os}}/{{.Architecture}}' "$db_image"
trivy image --image-src docker --scanners vuln --severity HIGH,CRITICAL \
  --ignore-unfixed --exit-code 1 "$db_image"
```

Use an approved Trivy installation with a current vulnerability database. Retain
its version, database metadata, report and scanned image ID in the private release
record. These [Trivy options](https://trivy.dev/docs/latest/guide/references/configuration/cli/trivy_image/)
apply the weekly database workflow's vulnerability threshold to the local candidate.
A failed scan or a remaining finding at that threshold stops rollout for review;
a clean result is limited to that scanner, database and threshold. A locally built
image may have no registry digest, so retain its full image ID. Do not select the
candidate using `docker compose images`: that command reports images used by
[created containers](https://docs.docker.com/reference/cli/docker/compose/images/),
which can still be running the old build.

#### Recreate the database after approval

1. Record the running database image ID and current PostgreSQL/PostGIS versions.
   Take and authenticate a fresh backup, run its `--verify-only` check, and confirm
   a successful restore drill into a separate destination and access to the matching
   encryption key. Follow [backup and recovery](BACKUP_RESTORE.md#postgresql-compose-backup-and-recovery).
   Keep the recovery point and previous images available off-host as appropriate.
2. Obtain explicit release approval for the candidate image ID, scan result,
   backup/recovery evidence and planned interruption before stopping services or
   recreating containers. Honour the same deployment lock as automatic releases.
   Do not combine this procedure with a PostgreSQL major-version change: that needs
   a separately tested dump/restore migration, not reuse of the old data volume.
3. Confirm the tag still identifies the scanned image, then stop the API and
   recreate only the database. Preserve the existing Compose project and volume:

   ```bash
   set -e
   test "$(docker image inspect --format '{{.Id}}' "$db_tag")" = "$db_image"
   docker compose stop api
   docker compose up -d --no-deps --no-build --pull never --force-recreate \
     --wait --wait-timeout 120 db
   test "$(docker inspect --format '{{.Image}}' "$(docker compose ps -q db)")" = "$db_image"
   docker compose ps db
   ```

   `--no-build --pull never` prevents a different build or pulled image from replacing
   the scanned candidate. The [Compose up options](https://docs.docker.com/reference/cli/docker/compose/up/)
   provide the explicit recreation and health wait. Stop if identity or health
   verification fails; keep the API stopped while investigating the approved
   recovery plan. Do not delete volumes or assume an older database image can read
   data changed by an upgrade.
4. Compare database and extension versions with the recorded baseline and intended
   target. Run this read-only check before the refresh and again after recreation:

   ```bash
   docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
   SHOW server_version;
   SELECT postgis_full_version();
   SELECT extname, extversion FROM pg_extension WHERE extname LIKE 'postgis%';
   SQL
   ```

   After an approved PostGIS version change, run `SELECT postgis_extensions_upgrade();`
   in the application database during the maintenance window, then repeat the
   version checks. An Alpine-only refresh does not require that extension update.
5. Start the existing API with `docker compose start api`. Verify container health,
   HTTPS `/api/health` and `/api/ready`, sign-in and reading a saved report. Record
   the running image ID and validation results before closing the maintenance work.

#### API, parser and web security refreshes

The same cache issue applies to `backend/Dockerfile` (`apt-get update` and
`apt-get upgrade`) and the final stage of `frontend/Dockerfile` (`apk upgrade`).
Ordinary source changes can leave these earlier layers cached. The parser uses
the backend Dockerfile under its own Compose service/image tag, so include it in
an authorised application-image refresh:

```bash
set -e
docker compose build --pull --no-cache api parser web
```

Identify and scan each resulting `<project>-api`, `<project>-parser` and
`<project>-web` image by its full ID, following the same candidate checks above.
Review relevant Python, Caddy/Go and JavaScript findings too: rerunning a build
does not update pinned bases, locked application dependencies or the locked Caddy
build. Such changes need their own reviewed dependency updates and tests.

Apply the same verified-backup, release-approval and deployment-lock requirements
before replacing application containers. Use a reviewed rollout that selects the
scanned image IDs without rebuilding or pulling a replacement, preserves the
database, and verifies running identities, health/readiness, parser health, frontend
loading and sign-in. The [automatic deployment controller](AUTOMATIC_DEPLOYMENT.md)
builds its own application images; an earlier manual or CI scan does not establish
the identity or package contents of that later build.

## Backups and recovery

Use the [backup and restore guide](BACKUP_RESTORE.md) for SQLite and PostgreSQL commands. Retain the application revision, configuration and encryption key needed to restore each recovery point. Copy backups off the application host and practise restoration into a fresh destination.

`backup.py` and `restore.py` never schedule, prune or delete anything. The repository installs no backup schedule: you add `scheduled_backup.py` to the host's crontab yourself. Once scheduled, it deletes its own oldest `scheduled-*.tar.gpg` archives beyond `--keep` (default 30, minimum 3) after each successful run, and never touches other files, manual bundles or off-site copies. The automatic deployment workflow creates a verified backup before a release, which complements a regular backup policy; the operator-run [deployment pruning script](AUTOMATIC_DEPLOYMENT.md#pruning-old-releases) removes old pre-release backups only when you run it.

## Common problems

| Symptom | First checks |
| --- | --- |
| HTTPS fails | DNS, certificate trust and web-service logs |
| API restarts | Required secrets, writable data directory and migration logs |
| Sign-in or cookies fail | Browser URL matches `ASE_PUBLIC_BASE_URL`, including HTTPS |
| Sources show waiting or blocked | Source status details, credentials, upstream availability and next poll time |
| Research cannot start | Tested AI connection, account permissions and model allowance |
| Reports or updates are slow | Memory pressure, disk capacity and provider response times |

Do not publish environment files, detailed recovery records or unredacted logs when asking for help.

## Container privilege and proxy boundary

Compose reserves Caddy's address on a dedicated proxy network and gives Uvicorn
only that address as `ASE_FORWARDED_ALLOW_IPS`. Other peers' forwarded headers are
ignored. The standalone API image trusts loopback only. If the default subnet
conflicts with an existing network, set `ASE_PROXY_SUBNET`, `ASE_PROXY_WEB_IP`
and `ASE_PROXY_API_IP` together. The web and API addresses must be distinct,
free usable addresses in that subnet. Both are explicit so the API cannot
take Caddy's reserved address before the web container starts. Recreate the
network through the reviewed manual rollout and verify client IPs and rate limits.
Do not override trust with `*`.

API runs with all Linux capabilities dropped. PostgreSQL drops all capabilities
and adds only CHOWN, DAC_OVERRIDE, FOWNER, SETGID and SETUID for its root entrypoint
to prepare volume ownership and become postgres. Removing those too requires
pre-provisioned volume ownership and a separately tested entrypoint. Both containers
set no-new-privileges. Validate a new empty database volume and an existing volume
before an authorised release; no production volume is changed by development tests.

For a planned application-key change, follow [encryption-key rotation](ENCRYPTION_KEY_ROTATION.md). Keep each database backup with its matching recoverable key version.
