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

The API applies migrations on startup. The administrator command prompts for a password. Sign in through the configured browser URL and enrol MFA. Authenticator apps work without SMTP; email codes require a configured mail relay.

Check both `/api/health` and `/api/ready` over HTTPS, load the interface and confirm that anonymous requests cannot open administration. Review source health in **Administration → Sources**. Upstream refusals, missing credentials and a source waiting for its next poll have different causes.

For public HTTPS, DNS must resolve to your host and the certificate challenge must be reachable. For internal certificates, establish trust on your own client devices. Enable a non-zero HSTS duration only after HTTPS works reliably; browsers retain that policy until it expires.

## Operation and updates

**Run one API process.** The live event store, rate limits and several coordination locks are process-local. Multiple API replicas or Uvicorn workers are not supported by this deployment design.

Keep time synchronisation enabled. Watch memory, disk capacity, source status, model usage and job failures. Compose bounds each service's container logs (json-file, five 20 MB files) and sets memory and process limits sized from the reference host; raise `mem_limit` in `docker-compose.yml` if a real workload needs more, since an API that reaches its limit is restarted and its live store warms up again. Arrange retention for any logs you ship elsewhere.

Caddy serves pre-compressed Brotli and gzip copies of the web client. Content-hashed files under `/assets/` are cached for a year as immutable; `index.html` and other fixed names revalidate on every visit, so a deploy reaches returning browsers immediately. A missing `/assets/` file answers 404 rather than the application shell.

Before an update, review migration requirements, take and verify a backup, and check the target revision passed CI. An update restarts application processes: live feeds warm up again and running research may be interrupted. Verify health, readiness and sign-in after the update. Restoring application images does not reverse a database migration.

The repository also provides an [automatic deployment workflow](AUTOMATIC_DEPLOYMENT.md). Its controller is installation-specific and must be reviewed and adapted before use on another host.

## Backups and recovery

Use the [backup and restore guide](BACKUP_RESTORE.md) for SQLite and PostgreSQL commands. Retain the application revision, configuration and encryption key needed to restore each recovery point. Copy backups off the application host and practise restoration into a fresh destination.

The scripts do not install a backup schedule or delete old backups. Choose those policies explicitly. The automatic deployment workflow creates a verified backup before a release, which complements a regular backup policy.

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
