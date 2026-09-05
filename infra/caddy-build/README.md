# Standard Caddy build

The web image builds Caddy 2.11.4 from its published Go module because the
corresponding official image contains vulnerable Go dependencies. The wrapper
uses the upstream command and standard module imports, including timezone data.
The Dockerfile preserves the official database-exclusion tags and restores the
binary's low-port capability after copying it into the official Alpine runtime.
The wrapper follows the [upstream entry point](https://github.com/caddyserver/caddy/blob/v2.11.4/cmd/caddy/main.go)
and [release build settings](https://github.com/caddyserver/caddy/blob/v2.11.4/.goreleaser.yml).

`go.mod` and `go.sum` lock the patched dependency graph. The build uses a pinned
Go 1.26.6 image, disables automatic toolchain downloads and verifies module
checksums before compiling with `-mod=readonly`. Alpine security updates are
applied at image build time, so the final image digest must be recorded and
scanned for each release.

To refresh the lockfiles, run `go mod tidy` with the pinned Go toolchain after
editing the intended versions. Review transitive changes, then build from the
repository root:

```sh
docker build --pull --no-cache -f frontend/Dockerfile -t ase-web:check .
docker run --rm ase-web:check caddy version
docker run --rm ase-web:check caddy list-modules
docker run --rm ase-web:check caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
trivy image --scanners vuln --severity HIGH,CRITICAL --exit-code 1 ase-web:check
```

`--no-cache` ensures the Alpine update step runs again for a release build.
Before release, compare `caddy version` and `caddy list-modules` with the selected
official release, validate `infra/Caddyfile`, exercise static and API proxy
routes locally, and scan the final image for vulnerabilities. This is a standard
Caddy build maintained by this repository, not an unchanged upstream binary.
Once an official image passes the same checks, the extra build stage can be
removed together with this directory.
