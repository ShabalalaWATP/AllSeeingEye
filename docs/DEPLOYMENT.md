# Deploy to a virtual private server

The app is a long-lived process, not a set of functions: it polls hundreds of sources on
their own intervals, keeps raw events in a bounded in-memory store that never reaches the
database, and runs report jobs that can take forty minutes. It therefore needs a machine
that stays on, not a serverless platform. The Compose stack in this repository is the
deployment: PostgreSQL with PostGIS, the API container, and Caddy serving the built
interface and proxying `/api` on the same origin.

Everything below assumes Debian 13 or a current Ubuntu LTS on the server and Git Bash (or
any POSIX shell) on your own machine. Docker publishes packages for both, including Ubuntu
26.04 (`resolute`). Commands prefixed `you$` run locally; `server$` runs on
the server over SSH.

## Before you start

| Need | Notes |
| --- | --- |
| A server | 4 vCPU, 8 GB memory, 80 GB disk. Hetzner CX33 is about £8.50 a month; other providers charge two to four times that for the same memory. 4 GB will run it, but the live store alone is budgeted 512 MB and that budget is an estimate rather than a hard cap. |
| A domain | Any name you control, with access to its DNS records. Caddy obtains the certificates itself. |
| An SSH key | `ssh-keygen -t ed25519` if you do not have one. Password logins are disabled below. |
| Your provider keys | The OpenAI key and any feed keys you use locally. They are entered once into `.env` or the admin interface, never into the repository. |

Budget context: the server costs less than the model usage. A heavy day measured on this
deployment was about 63 pence of model spend, roughly £19 a month, against about £8.50 for
the machine. Prices here were read from the Hetzner console in September 2026 and include
VAT; check the current figures before buying.

## 1. Create the server

Written for Hetzner Cloud, which is the cheapest sound option without a commitment. Other
providers differ only in this step.

1. Register at **console.hetzner.cloud** and add a payment method. New accounts are
   sometimes held for identity verification, which can take from minutes to a day, so do
   this before you plan the rest.
2. Create a **project** (any name), then **Add Server**:
   - **Location**: Falkenstein, Nuremberg or Helsinki for the UK.
   - **Image**: Debian 13.
   - **Type**: Shared Resources, **Cost-Optimized**, architecture **x86**, then **CX33**
     (4 vCPU, 8 GB, 80 GB, about €10 a month). The Regular Performance (CPX) tab sells the
     same memory for roughly four times as much. Cost-Optimized is marked limited
     availability, so if CX33 is greyed out in your location either choose another location
     or fall back to CPX32. Never choose the Arm64 line: the Dockerfiles pin images by
     digest and several of those pins are amd64 only.
   - **Networking**: keep IPv4 and IPv6. A public IPv4 carries a small monthly charge and
     you need one for a domain most people can reach.
   - **SSH keys**: add your public key here, so it is installed for `root` at first boot.
   - **Backups**: optional, 20 per cent of the server price. Worth taking. It rolls the
     whole machine back, which covers different failures from the database backups in
     step 10; neither replaces the other.
3. Note the IPv4 address once it boots.

Then create a **cloud firewall** (Firewalls, Create Firewall) and apply it to the server,
with three inbound rules and nothing else:

| Port | Protocol | Source |
| --- | --- | --- |
| 22 | TCP | Your own address, or `0.0.0.0/0` and `::/0` if it changes often |
| 80 | TCP | `0.0.0.0/0` and `::/0` |
| 443 | TCP | `0.0.0.0/0` and `::/0` |

This firewall runs outside the machine, so unlike a host firewall it also gates ports that
Docker publishes. Leave outbound unrestricted: the app polls hundreds of sources.

If you ever lock yourself out of SSH, the console has a web terminal and a rescue mode.

## 2. Point the domain at it

Create two DNS records at your registrar, replacing the address with your own:

```
A     eye.example.org      198.51.100.10
AAAA  eye.example.org      2a01:4f8:...      (only if the server has IPv6)
```

Certificate issuance fails until this resolves, so do it now and check before step 7:

```bash
you$ dig +short eye.example.org
```

## 3. First login and hardening

```bash
you$ ssh root@198.51.100.10
```

Create a working account, give it your key and sudo, then lock down SSH:

```bash
server$ adduser --disabled-password --gecos "" ase
server$ usermod -aG sudo ase
server$ install -d -m 700 -o ase -g ase /home/ase/.ssh
server$ cp /root/.ssh/authorized_keys /home/ase/.ssh/ && chown ase:ase /home/ase/.ssh/authorized_keys
server$ sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/; s/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
server$ systemctl restart ssh
```

Ubuntu images ship drop-in files under `/etc/ssh/sshd_config.d/`, which are read before
the main file, and the first value obtained wins. Editing the main file can therefore be
overridden without warning, so check what the daemon actually resolved:

```bash
server$ sshd -T | grep -E 'permitrootlogin|passwordauthentication'
```

Both must read `no`. If either still says `yes`, write a drop-in that sorts ahead of the
image's own and restart again:

```bash
server$ printf 'PermitRootLogin no
PasswordAuthentication no
' > /etc/ssh/sshd_config.d/01-hardening.conf
server$ systemctl restart ssh && sshd -T | grep -E 'permitrootlogin|passwordauthentication'
```

Open a **second** terminal and confirm `ssh ase@198.51.100.10` works before closing the
first one. Then, as `ase`:

```bash
server$ sudo apt-get update && sudo apt-get upgrade -y
server$ sudo apt-get install -y ufw unattended-upgrades
server$ sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw --force enable
server$ sudo dpkg-reconfigure -plow unattended-upgrades   # answer Yes
```

Add swap so a long report cannot trigger the out-of-memory killer:

```bash
server$ sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
server$ sudo mkswap /swapfile && sudo swapon /swapfile
server$ echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

`ufw` here is defence in depth, not the main gate. Docker publishes ports through its own
iptables chains, so a host firewall does not block a published container port; the cloud
firewall from step 1 does. Only 80 and 443 are published in any case, and the API and the
database are reachable only from inside the Compose network. Keep it that way.

## 4. Install Docker

```bash
server$ curl -fsSL https://get.docker.com | sudo sh
server$ sudo usermod -aG docker ase
server$ exit
```

Log in again so the group applies, then cap the log files, because the feed scheduler
writes continuously and the default json driver never rotates:

```bash
server$ sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{ "log-driver": "json-file", "log-opts": { "max-size": "20m", "max-file": "5" } }
JSON
server$ sudo systemctl restart docker && docker run --rm hello-world
```

## 5. Copy the application to the server

`main` exists only on your machine, so ship the tracked files directly rather than
publishing the repository. From the repository root:

```bash
you$ ssh ase@198.51.100.10 'mkdir -p ~/ase'
you$ git archive --format=tar HEAD | ssh ase@198.51.100.10 'tar -x -C ~/ase'
```

That sends exactly what is committed: no `.env`, no `node_modules`, no `.venv`, no local
database. Use the same command for every later update.

## 6. Configure the deployment

```bash
server$ cd ~/ase && cp .env.example .env && chmod 600 .env
server$ openssl rand -base64 48   # run three times, one value per secret below
```

Edit `.env` (`nano .env`) and set at least these. Everything else can keep its default
until you need it:

```ini
ASE_ENV=prod
ASE_JWT_SECRET=<first generated value>
ASE_ENCRYPTION_KEY=<second generated value>
POSTGRES_PASSWORD=<third generated value>
ASE_PUBLIC_BASE_URL=https://eye.example.org
ASE_SITE_ADDRESS=eye.example.org
ASE_TLS=you@example.org          # your email: switches Caddy to real certificates
ASE_HSTS_MAX_AGE=0               # leave 0 until HTTPS is confirmed working, then step 9
ASE_FEEDS_CONTACT=you@example.org
ASE_LOG_LEVEL=INFO
```

Leave `ASE_DATABASE_URL` alone: Compose builds the PostgreSQL URL from the `POSTGRES_*`
values and overrides it for the API container. Add your provider keys now if you like, or
enter them later through the admin interface, which stores them encrypted with
`ASE_ENCRYPTION_KEY`.

Keep a copy of `ASE_ENCRYPTION_KEY` somewhere separate from the server. Losing it makes
every stored provider key unreadable, and backups that exclude it cannot restore them.

The API container runs as uid 10001 and writes the satellite cache and backups into the
bind-mounted `data` directory, so give it ownership before the first start:

```bash
server$ mkdir -p data && sudo chown -R 10001:10001 data
```

The web container also runs as uid 10001. A new named Caddy volume inherits the image's
ownership. When upgrading a deployment that already has `caddy_data` or `caddy_config`,
build the new image and migrate those two volumes once before starting it:

```bash
server$ docker compose build web
server$ docker compose run --rm --user root --cap-add CHOWN --entrypoint sh web -c 'chown -R 10001:10001 /data /config'
```

## 7. Build and start

```bash
server$ docker compose up -d --build
```

The first build takes several minutes: it compiles Caddy, builds the interface and installs
the Python environment. The API container applies database migrations on start, so no
separate migration step is needed. Watch it settle:

```bash
server$ docker compose ps
server$ docker compose logs -f api   # Ctrl-C to stop following
```

Expect `Application startup complete` from the API and, in the `web` logs, a certificate
obtained for your domain. Then check from your own machine:

```bash
you$ curl -sS https://eye.example.org/api/health
```

A JSON health response over valid HTTPS means the stack is up. If the certificate failed,
see Troubleshooting below.

## 8. Create the administrator and enrol MFA

```bash
server$ docker compose exec api ase create-admin --email you@example.org --display-name "Your Name"
```

It prompts for a password, twice, and does not echo it. Then open
`https://eye.example.org`, sign in, and enrol a factor immediately: administrators require
an MFA-verified session and mandatory enrolment when no factor exists.

Use an **authenticator app** unless you have configured SMTP in `.env`; email codes need a
working mail relay. If you are ever locked out, `docker compose exec api ase
recover-admin-mfa --help` and `recover-admin-totp --help` describe the recovery paths.

## 9. Turn on HSTS

Only once HTTPS is confirmed working, because the policy tells browsers to refuse plain
HTTP for this host for a year and cannot be withdrawn quickly:

```bash
server$ sed -i 's/^ASE_HSTS_MAX_AGE=0/ASE_HSTS_MAX_AGE=31536000/' .env
server$ docker compose up -d web
you$ curl -sSI https://eye.example.org | grep -i strict-transport
```

## 10. Schedule backups

Nothing is scheduled by design. The stack is running PostgreSQL, so use the Postgres path
from `docs/BACKUP_RESTORE.md`. Backups need Python and the repository, which are already on
the server:

```bash
server$ sudo apt-get install -y python3
server$ install -m 700 -d ~/backups
server$ install -m 700 -d ~/.config/all-seeing-eye
server$ python3 -c "import secrets; open('/home/ase/.config/all-seeing-eye/backup-auth.key', 'wb').write(secrets.token_bytes(32))"
server$ chmod 600 ~/.config/all-seeing-eye/backup-auth.key
server$ crontab -e
```

Keep this authentication key outside the repository, `.env` and backup directories. Copy
it to separate protected recovery storage. Losing it prevents authenticated PostgreSQL
restore, while disclosure lets an attacker forge a bundle.

Add a nightly run and a weekly prune:

```cron
17 3 * * * cd /home/ase/ase && /usr/bin/python3 scripts/backup.py postgres --authentication-key-file /home/ase/.config/all-seeing-eye/backup-auth.key --output /home/ase/backups/postgres-$(date -u +\%Y\%m\%d_\%H\%M\%S) >> /home/ase/backups/backup.log 2>&1
23 4 * * 0 find /home/ase/backups -maxdepth 1 -name 'postgres-*' -mtime +30 -exec rm -rf {} +
```

Then do the parts cron cannot do for you:

1. Run it once by hand and verify: `python3 scripts/backup.py postgres --authentication-key-file ~/.config/all-seeing-eye/backup-auth.key --output ~/backups/manual` then `python3 scripts/restore.py ~/backups/manual --authentication-key-file ~/.config/all-seeing-eye/backup-auth.key --verify-only`.
2. Copy backups off the machine regularly. A server backup stored only on that server is not a backup.
3. Store `ASE_ENCRYPTION_KEY` separately from the bundles, as in step 6.
4. Rehearse a restore into a fresh database before you need one. `docs/BACKUP_RESTORE.md` has the drill.

## Updating

```bash
you$ git archive --format=tar HEAD | ssh ase@198.51.100.10 'tar -x -C ~/ase'
server$ cd ~/ase && docker compose up -d --build
```

Migrations run automatically as the API container starts. Take a backup first when the
update includes a migration. To roll back, ship an earlier commit the same way; note that
database migrations do not roll back on their own, so restore from backup if one applied.

## Operating notes

- **Run exactly one API process.** Never add `--scale api=2` or uvicorn workers. The live
  event store, rate limits, the search lock and export slots are all process-local; a
  second process would silently halve the rate limits and split the event store.
- **Keep the parser service isolated.** Compose starts one `parser` sidecar with no network,
  a read-only root filesystem, a 768 MiB memory limit, 64-process limit and 128 MiB `/tmp`.
  Do not attach it to a network or remove those resource limits. The API exchanges only
  bounded messages through the `parser_socket` Unix-socket volume.
- **Memory is the constraint to watch.** `docker stats` during a report run tells you
  whether 8 GB is comfortable. If the API container is killed, raise the server size or
  lower `ASE_LIVE_STORE_MEMORY_MB`.
- **Expect some sources to behave differently here.** Several publishers already refuse
  this client (CISA, the ACSC, CBC), and Cloudflare-fronted sites treat datacentre
  addresses more harshly than home connections, so a few feeds that work locally may start
  refusing. Check Administration after a week and compare with
  `docs/NEWS_SOURCE_COVERAGE.md`.
- **The clock matters.** Token expiry, the scheduler and report windows are all UTC. Leave
  the server on UTC with time synchronisation enabled, which is the default.
- **Logs**: `docker compose logs --since 1h api`. Audit events for authentication and
  administration are in the database, not the container log.

## Before you widen access beyond yourself

`docs/security/PHASE6_ASVS_REVIEW.md` records eight public-exposure gates. Steps 3, 6, 7
and 9 above cover the transport and configuration ones. These remain yours to close:

1. Run an authenticated OWASP ZAP baseline against this stack and resolve the findings.
   The review explicitly authorises no production scan on its own.
2. Complete the ASVS level 2 checklist for authentication recovery and access-token
   revocation expectations.
3. Rotate any provider key that has ever been pasted into a chat, a terminal or a shared
   document, including during development.
4. Re-run the dependency, secret and image scans against the artefacts you actually
   deployed, not the ones built locally.
5. Decide log, audit and usage retention for this machine, and confirm the restore drill in
   step 10 against your own recovery procedure.

Invalid passwords and MFA codes do not persistently lock the named account. The existing
IP and email rate limits are process-local, so a public deployment should still restrict
reachability where practical. For a VPN such as Tailscale, set `ASE_SITE_ADDRESS` to the
Tailscale hostname and `ASE_TLS=internal`.

## Troubleshooting

**The certificate never arrives.** Check that `dig +short eye.example.org` returns the
server address, that ports 80 and 443 are open (`sudo ufw status`), and read
`docker compose logs web`. Caddy needs port 80 reachable for the challenge. Rate limits at
the issuer apply after several failed attempts, so fix the cause before retrying.

**The API container restarts in a loop.** `docker compose logs api`. The usual causes are a
missing `ASE_JWT_SECRET` (required when `ASE_ENV=prod`), a `data` directory the container
cannot write (step 6), or a migration failure, which names the revision it stopped on.

**Signing in fails with a session error.** `ASE_PUBLIC_BASE_URL` must match the address in
the browser exactly, including `https://`, or the cookies are rejected.

**Everything is slow, or reports pause.** Check `docker stats` for memory pressure and
`docker compose logs api | grep -i budget` for model allowance exhaustion. A paused report
resumes from its completed sections on the job page.
