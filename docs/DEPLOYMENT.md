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

Commercial source enforcement is opt-in with `ASE_COMMERCIAL_USE=true`; its
default is `false`. Review [source licences](SOURCE_LICENCES.md) before enabling
it. Set `ASE_SOURCE_LICENCE_ACKNOWLEDGEMENTS` only to exact catalogue IDs for which
you have permission covering the installation and intended use. This is a
comma-separated list, not a wildcard or a place for credentials or correspondence.
Unverified and partly reviewed sources remain unavailable without that explicit
acknowledgement. Forbidden sources, including EOX imagery, cannot be opened by
acknowledgement, an API key or administrator activation.

Restart after changing these settings. Startup validates packaged metadata and
reports refused source IDs without logging credentials. Check Administration,
Sources and the user Source catalogue for effective availability, then verify
the permitted map styles and workflows. Enabling the technical control does not
approve a commercial offer, buy a licence or authorise a production release.

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

Compose builds the database from `infra/postgis/Dockerfile`: the digest-pinned upstream PostGIS image with Alpine security updates applied and the Go-built `gosu` replaced by Alpine's `su-exec`. Application updates never rebuild or restart it, so its system packages age until you rebuild it. Automatic deployment refuses changes under `infra/postgis/` until they are rolled out manually. Rebuild it when the base pin changes or when the weekly `Database image` workflow turns red, and otherwise at least monthly:

1. Take and verify a backup, then stop the API.
2. `docker compose build --pull db`, then `docker compose up -d --no-deps db`, and wait until it is healthy.
3. After a PostGIS version change, run `SELECT postgis_extensions_upgrade();` in the application database and confirm the versions in `pg_extension`.
4. Start the API and verify health, readiness and sign-in.

The same PostgreSQL major version reuses the data volume. A major version change needs a dump and restore, never an image change alone.

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
