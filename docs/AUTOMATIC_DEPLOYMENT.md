# Automatic VPS deployment

Merging into `main` starts the existing **CI** workflow. After all its jobs pass,
**Deploy VPS** deploys that exact commit to `https://allseeingeyeosint.com`.
Pull requests, failed/cancelled CI runs and superseded commits cannot deploy.
Deployment status and failures appear in GitHub Actions and the `production`
environment. A merge is not live until its deployment job succeeds.

## Release process

1. Check the successful push CI revision is still the repository's `main` head.
2. Connect using a dedicated SSH key and a pinned server host key.
3. Take a non-blocking host lock; refuse a dirty checkout, diverged history,
   missing backup key or less than 6 GiB of free disk.
4. Build API/parser and web images from a temporary worktree at the tested SHA.
   Running services stay online during the build.
5. Create and authenticate a PostgreSQL backup using the existing backup tools.
6. Recheck `main`, fast-forward the VPS checkout and replace API, parser and web.
   The database service, named volumes and `.env` stay in place.
7. Verify container image IDs, Compose health, public HTTPS health/readiness,
   the frontend JavaScript asset and anonymous administration rejection.
8. On a failed cutover, restore the previous checkout and application images,
   then verify them. The Actions run remains failed even if rollback succeeds.

There is a brief service restart, not zero-downtime deployment. In-memory feeds
warm up again; running research jobs can be interrupted. Deployments are serial
and newer merges do not cancel an active cutover. A lost runner connection can
leave an uncertain result: check the host and the recovery record before retrying.
An already-deployed retry verifies image revision labels as well as health.

## Deliberate manual gates

Changes to `docker-compose.yml`/standard Compose filenames, Alembic configuration
or migrations, or the migration runner require a reviewed manual rollout. The
API migrates on startup; automatically reverting images would not undo a schema
change. Automatic deployment never restores or downgrades the database.

The two deployment controller scripts also require explicit installation by an
operator. Their exact contents must match the target commit before that commit
can deploy. Updating repository scripts alone cannot replace the root-owned SSH
controller. Normal backend, frontend, dependency and Caddy changes deploy through
the pipeline.

## Installed configuration

The existing host is `ase@89.167.102.143`, SSH port `2222`, checkout
`/home/ase/ase`, Compose project `ase`. The host already has Git, Docker Compose,
Python 3 and curl. No self-hosted Actions runner or extra inbound port is needed.

GitHub environment `production` permits branch `main` only, with no approval
prompt for normal releases:

| Setting | Purpose |
| --- | --- |
| Environment secret `VPS_DEPLOY_KEY` | Dedicated Ed25519 private key, not the operator's personal key |
| Environment variable `VPS_KNOWN_HOSTS` | `[89.167.102.143]:2222` host key obtained over the existing trusted SSH connection |

The server's `authorized_keys` entry uses `restrict` and forces
`/usr/bin/python3 -E -s /usr/local/lib/ase-deploy/deploy_ssh.py`. The only accepted
commands are `check FULL_SHA` and `deploy FULL_SHA`; shells, file transfer,
forwarding, agent forwarding and PTYs are unavailable to that key. Deployment
runs as `ase`, which already has Docker access. Merged application code and
Dockerfiles remain trusted production code; this is not a sandbox for main.

The controller directory and both files are root-owned, directory mode `755`,
file mode `644`. Install reviewed controller changes using the operator SSH key:

```bash
scp -P 2222 scripts/deploy_vps.py scripts/deploy_ssh.py ase@89.167.102.143:/home/ase/
ssh -p 2222 ase@89.167.102.143 \
  'sudo install -d -m 755 /usr/local/lib/ase-deploy && sudo install -o root -g root -m 644 /home/ase/deploy_vps.py /home/ase/deploy_ssh.py /usr/local/lib/ase-deploy/'
```

Keep database credentials, encryption keys and the backup authentication key on
the VPS. None are copied into GitHub. The production secret can be removed to
disable deployment access; disabling **Deploy VPS** stops automatic triggers.
Key rotation must replace both the dedicated authorised public key and the
environment secret while preserving the operator's existing key.

## Recovery and operation

Each attempted release stores a private record under
`/home/ase/deployments/<sha-prefix>-<random>/`: `release.json` identifies previous
and target commits and immutable rollback image IDs; `backup/` contains the
verified backup; `success` appears only after verification. Images have
`release-<full-sha>` and `rollback-<previous-sha>` tags. Temporary build worktrees
are removed after completion. Backups and images are retained, not automatically
deleted; review disk usage and copy recovery material off-host regularly.

For a failed build or backup, the old application remains running. For a failed
rollback, inspect `docker compose ps`, the recovery record and the recorded
images using the operator key. Do not blindly reset a changed checkout or restore
a database. Use [the recovery runbook](BACKUP_RESTORE.md) for database recovery.
Subprocess output is withheld from Actions to avoid logging environment values;
an operator can rerun the reported failed build/check directly on the host.

To retry a transient failure, re-run the successful **push-triggered CI** run for
the current `main` commit from GitHub Actions. A manual `workflow_dispatch` CI run
does not deploy. To check connectivity without changing the release, use the
dedicated key with `check <current-main-sha>`. The host lock is
`/home/ase/deployments/deployment.lock`; manual releases must honour it too.

Workflow security follows GitHub's guidance on
[workflow-run privileges](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run)
and [deployment environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).
The privileged workflow never checks out PR code or downloads CI artefacts.
