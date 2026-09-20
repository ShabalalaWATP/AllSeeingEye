# Set up The All Seeing Eye

Run the app locally on Windows 11, macOS or Linux. Choose one route:

| Route | Best for | What runs locally |
| --- | --- | --- |
| [Native development](#native-development) | Editing and debugging the app | Python API, SQLite database and Vite frontend |
| [Docker Compose](#docker-compose) | Running the complete packaged app | API, PostgreSQL/PostGIS, isolated document parser and HTTPS web server |

Both routes need internet access to install dependencies and collect public data. Browsing the map does not require an AI account. AI features need a configured model connection, which may incur provider charges.

## Install the tools

### Windows 11

Use PowerShell. Install [Git for Windows](https://git-scm.com/downloads/win), [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Node.js](https://nodejs.org/en/download). For native development, use Node 22.22 or later (Node 24 LTS recommended) and Python 3.13, which `uv` can install for you.

For the container route, install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/), follow its WSL 2 prerequisites and select Linux containers. Start Docker Desktop before running Compose. Host Python and Node are not needed for this route.

### macOS

Use Terminal. Install Git, [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Node.js](https://nodejs.org/en/download). Apple's Command Line Tools provide Git; run `xcode-select --install` if it is missing. Use Node 22.22 or later (Node 24 LTS recommended) and Python 3.13 for native development.

For containers, install [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/) for your processor and start it. The repository pins an AMD64 database image. On Apple Silicon, use AMD64 emulation for this stack as described below. This is not a native ARM64 container build.

### Linux

Install Git through your distribution's package manager, then install [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Node.js](https://nodejs.org/en/download). Use Node 22.22 or later (Node 24 LTS recommended) and Python 3.13 for native development.

For containers, install [Docker Engine](https://docs.docker.com/engine/install/) and the [Compose plugin](https://docs.docker.com/compose/install/). Follow Docker's instructions for allowing your account to run Docker commands. These instructions target an x86-64 Linux host; ARM hosts need compatible AMD64 emulation for the pinned database image.

### Get the code

Open a new terminal after installing tools so it picks up changes to `PATH`.

The same commands work in PowerShell and Terminal:

```text
git clone https://github.com/ShabalalaWATP/AllSeeingEye.git
cd AllSeeingEye
```

All commands below start in this repository unless a different directory is stated. Do not overwrite an existing `.env` file or regenerate keys for an existing installation.

## Native development

### 1. Install the locked dependencies

```text
uv python install 3.13
cd backend
uv sync --frozen --python 3.13
cd ../frontend
npm install --global pnpm@11.25.0
pnpm install --frozen-lockfile
cd ..
```

`pnpm@11.25.0` matches the repository's `packageManager` setting. Python 3.12 is the minimum supported version; 3.13 matches the backend container and CI setup.

If PowerShell blocks an npm or pnpm script, use `npm.cmd` or `pnpm.cmd` for that command. If a global npm installation fails because of permissions, use a user-owned Node installation following the [pnpm installation guide](https://pnpm.io/installation).

### 2. Configure the backend

Create `backend/.env` in your editor with these settings. Replace the three explanatory values before starting:

```dotenv
ASE_ENV=dev
ASE_DATABASE_URL=sqlite+aiosqlite:///./data/ase.db
ASE_PUBLIC_BASE_URL=http://localhost:5173
ASE_JWT_SECRET=REPLACE_WITH_A_RANDOM_SECRET
ASE_ENCRYPTION_KEY=REPLACE_WITH_A_DIFFERENT_RANDOM_SECRET
ASE_FEEDS_CONTACT=REPLACE_WITH_YOUR_PROJECT_URL_OR_CONTACT_ADDRESS
```

Generate each secret separately with this command from the repository root:

```text
uv run --project backend python -c "import secrets; print(secrets.token_hex(48))"
```

Keep these values private. The JWT secret signs sessions. The encryption key protects saved provider credentials and authenticator secrets; keep a protected backup of it separately from the database. Changing that key makes existing encrypted values unreadable.

The root [`.env.example`](../.env.example) documents optional settings. Copy only those you need into `backend/.env`. Leave unused optional settings commented out rather than adding blank values. In particular, `ASE_JWT_SECRET=` is an explicit empty secret, not a request to generate one.

Settings and relative database paths are resolved from the backend's working directory. The database for this configuration is `backend/data/ase.db`. Native development does not read the root `.env` used by Compose.

### 3. Create the database and administrator

```text
cd backend
uv run ase migrate
uv run ase create-admin --email you@example.com --display-name "Your Name"
```

Use your own email address. The command prompts privately for a password and confirmation. Passwords must be 12 to 128 characters and pass the common-password checks. The administrator is created active; no email activation is needed for this first account.

### 4. Start both services

In the backend terminal:

```text
uv run uvicorn ase.main:app --reload --port 8001
```

Open a second terminal at the repository root:

```text
cd frontend
pnpm dev
```

Open [http://localhost:5173](http://localhost:5173). The frontend forwards `/api` requests to port 8001, so the browser uses one origin for sign-in and API calls. Keep using `localhost` consistently rather than switching between it and `127.0.0.1`.

Both development servers remain attached to their terminals. Use **Ctrl+C** in each to stop them. Keep this development setup on your own machine.

## Docker Compose

Compose includes its own Python, Node and media-processing tools. You need Git, a running Docker engine and the Compose plugin on the host.

### 1. Create local configuration

Copy the example once, then edit the new root `.env` file.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS or Linux:

```sh
cp .env.example .env
chmod 600 .env
```

Set these values, using three independently generated secrets:

```dotenv
ASE_JWT_SECRET=REPLACE_WITH_A_RANDOM_SECRET
ASE_ENCRYPTION_KEY=REPLACE_WITH_A_DIFFERENT_RANDOM_SECRET
POSTGRES_PASSWORD=REPLACE_WITH_A_THIRD_RANDOM_SECRET
ASE_PUBLIC_BASE_URL=https://localhost
ASE_SITE_ADDRESS=localhost
ASE_TLS=internal
ASE_HSTS_MAX_AGE=0
ASE_FEEDS_CONTACT=REPLACE_WITH_YOUR_PROJECT_URL_OR_CONTACT_ADDRESS
```

A password manager can generate the secrets. Use at least 32 random characters. Hexadecimal characters are convenient because the database password is placed into a connection URL; punctuation such as `@`, `:` or `/` would need URL encoding.

Alternatively, generate a fresh value each time with these commands.

Windows PowerShell:

```powershell
$aseSecretBytes = New-Object byte[] 48
$aseRandom = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$aseRandom.GetBytes($aseSecretBytes)
$aseRandom.Dispose()
[BitConverter]::ToString($aseSecretBytes).Replace('-', '').ToLowerInvariant()
```

macOS or Linux, with OpenSSL installed:

```sh
openssl rand -hex 48
```

Compose sets the API to production mode and builds its PostgreSQL URL from `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB`. It overrides the example's development mode and SQLite URL. Set `ASE_PUBLIC_BASE_URL` explicitly to `https://localhost`; the example's `http://localhost:5173` is for native development.

Do not change the password or encryption key casually after first startup. Changing `POSTGRES_PASSWORD` in `.env` does not update the password already stored inside PostgreSQL.

### 2. Start the stack

On an Apple Silicon Mac, first set the target platform in the same terminal:

```sh
export DOCKER_DEFAULT_PLATFORM=linux/amd64
```

Then, on all platforms:

```text
docker compose version
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

The first build downloads images and dependencies. The API applies database migrations on startup. Wait for the database, parser and API to become healthy before creating the account.

The stack publishes local web ports 80 and 443. Docker's default port mapping may also make them reachable from other devices, depending on your firewall. Keep the computer on a trusted network while setting up. API and database ports are not published.

On Linux, the API runs as user ID 10001 and needs write access to the repository's `data` directory. If that new directory is owned by root and the logs report permission errors, stop the API and set ownership for this app's directory:

```sh
docker compose stop api
sudo chown 10001:10001 ./data
docker compose up -d api
```

### 3. Trust the local HTTPS certificate

Caddy creates a local certificate authority. A container cannot automatically add its root certificate to your computer's trust store. Copy out the public root certificate from your own running stack:

```text
docker compose cp web:/data/caddy/pki/authorities/local/root.crt ./ase-local-root.crt
```

Trust that certificate on the computer where you will open the app:

- **Windows 11:** open the certificate, choose **Install Certificate**, select **Current User**, and place it in **Trusted Root Certification Authorities**.
- **macOS:** import it into Keychain Access, open its trust settings and trust it for SSL. Your system may request authorisation.
- **Linux:** add it to your distribution's trusted CA store. For Debian or Ubuntu:

  ```sh
  sudo cp ase-local-root.crt /usr/local/share/ca-certificates/ase-local-root.crt
  sudo update-ca-certificates
  ```

Some browsers maintain their own certificate store and need the same public certificate imported there. Restart the browser after installing it. Only trust a certificate copied from a stack you control; never export or share the CA's private key. See [Caddy's local HTTPS guidance](https://caddyserver.com/docs/automatic-https#local-https).

The copied `.crt` file is local setup material, not a repository change. Remove it after importing it or keep it outside the checkout.

### 4. Create the administrator

```text
docker compose exec api ase create-admin --email you@example.com --display-name "Your Name"
```

Enter a strong password at the prompt, then open [https://localhost](https://localhost).

To inspect startup failures or stop the stack:

```text
docker compose logs --tail 100 api parser web
docker compose stop
```

`docker compose start` starts the existing containers again. `docker compose down` removes containers but retains named volumes. Do not add `--volumes` unless you intend to delete the stored database and other volume data. Read [backup and restore](BACKUP_RESTORE.md) before making changes to an installation you use.

## First sign-in

1. Sign in with the administrator's email and password.
2. Enrol an authenticator when prompted. Scan the QR code in your authenticator app and enter its current code. The encryption key must be configured for this to work.
3. The administrator opens in **Administration**. Use **Return to research** to open the globe.
4. Check **Sources** for collection status. Sources begin polling when the API starts; the entire catalogue does not become live at once. Credentials, provider terms and upstream availability affect individual sources.
5. Open **AI connections** when you want AI features. Add your provider connection, test it and apply it to the required role. Saving a profile alone does not select it for use. See [AI configuration and behaviour](AI.md).
6. Under **Account > Security**, generate recovery codes and store them privately. See [MFA operations](MFA_OPERATIONS.md).

SMTP is optional if you use an authenticator. To enable email MFA and account emails, configure `ASE_SMTP_HOST` and `ASE_SMTP_FROM_EMAIL` together, then the port, TLS mode and credentials required by your mail provider. Email MFA requires working delivery; the app does not display email codes as a fallback.

## Optional capabilities

Source-specific keys and permissions are listed in [the sources guide](02_DATA_SOURCES.md). Do not enable every optional source merely to make the dashboard green. Some require an account, approved use or a licence acknowledgement.

For native image OCR, install Tesseract with English language data. Video extraction needs both FFmpeg and FFprobe. Use trusted packages for your operating system, then place the tools on `PATH` or set `ASE_RESEARCH_TESSERACT_PATH`, `ASE_RESEARCH_FFMPEG_PATH` and `ASE_RESEARCH_FFPROBE_PATH` to their installed executable paths. Compose includes these tools.

Native document and media imports run in a bounded child process. If the operating system cannot establish the required limits, the import is rejected. This can affect native macOS setups or constrained Windows sessions. Use the Compose route for its isolated Linux parser instead of disabling that check. Setting `ASE_ENV=prod` on a standalone native API also requires the Compose-style parser service; it is not a switch for native development.

Report generation attempts to archive cited public URLs with the Wayback Machine by default. Set `ASE_ARCHIVE_ENABLED=false` if you do not want that outbound step. With no model connection configured, ordinary feed collection still runs, while model-dependent features remain unavailable.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Login page cannot reach the API | Confirm the backend is running on port 8001 and Vite on 5173. Open the app through Vite, not the API port. |
| Port 5173 or 8001 is occupied | Stop the other local process or choose another port. For an API change, set `ASE_DEV_API_TARGET=http://127.0.0.1:NEW_PORT` in `frontend/.env.local` and restart Vite. Update `ASE_PUBLIC_BASE_URL` if the frontend port changes. |
| Administrator cannot enrol MFA | Check `ASE_ENCRYPTION_KEY`; for email MFA also check SMTP configuration and delivery. Restart the API after changing settings. |
| Sign-in is lost after restarting | Configure a stable JWT secret. Keep the same hostname and protocol, and check that HTTPS-only cookies are not forced on HTTP development. |
| Compose refuses to start | Run `docker compose config --quiet`; check that Docker is running, required secrets are set and ports 80/443 are free. |
| HTTPS warning remains | Check that you imported the root from this stack and that you are visiting `https://localhost`. Recreating the CA volume creates a different root. |
| No AI output | Check that the connection test passes and the connection is applied to the role. Check provider access, quotas and the app's usage limits. |
| A source is waiting or unavailable | Inspect its reason in **Sources**. Missing keys, provider restrictions, cooldowns and unpublished new data are distinct from collection failures. |
| Document import cannot run safely | Use the Compose parser. For native media, also check the trusted tool paths. |

Do not paste `.env` contents or provider keys into bug reports. Describe the failing action and include the relevant error with private information removed.
