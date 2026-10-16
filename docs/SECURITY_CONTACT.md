# Public security contact

The web image serves `/.well-known/security.txt` through Caddy, without login,
using the installation's public settings. It is a static UTF-8 file generated
at container startup. It does not contact any provider or send a message.

## Configure publication

- `ASE_PUBLIC_BASE_URL`: the installation's HTTPS origin, with an optional port
  and trailing slash. Paths, query parameters, credentials and fragments are
  rejected when publication is enabled. HTTP development origins still work
  when publication is disabled.
- `ASE_SECURITY_CONTACT`: one monitored `mailto:` address or HTTPS private
  reporting page. Empty or unset disables publication and returns 404.
- `ASE_SECURITY_POLICY`: optional HTTPS disclosure-policy URL. Empty uses this
  software project's GitHub security policy. Operators must review whether those
  practices apply to their installation and supply their own policy if different.

For the project maintainer's installation, the existing KAN-22 channels are
`https://github.com/ShabalalaWATP/AllSeeingEye/security/advisories/new` or the
maintainer's email listed in [SECURITY.md](../SECURITY.md). Other operators must
choose a contact responsible for their installation. Contact and policy URLs
cannot include credentials, queries or fragments. The file is public, so never
put secrets or private invitation links in these values.

Compose passes only these public settings to the web service. Existing installations
must explicitly set the contact before deploying this change to retain publication.
No production settings were changed as part of implementation. A blank contact is
an intentional disabled state, not a claim that a reporting channel is monitored.

The generator writes only `/tmp/ase-security-contact/security.txt`, under a private
directory owned by the non-root web user. Caddy reads that exact path with the
existing security headers and `text/plain; charset=utf-8`. The root filesystem
remains read-only. The contact route cannot use the SPA fallback; unknown
`/.well-known/` paths also return 404. Static image assets contain no deployment
hostname. Invalid enabled settings fail startup with a sanitised error.

## Review and expiry

`infra/caddy-build/security-contact/expiry.txt` retains the reviewed fixed expiry
of 1 October 2027. The generator requires an expiry no more than one year ahead;
restarting or rebuilding does not extend it. Review the monitored contact and
policy before editing this date, rebuilding and approving deployment.

CI's repository check warns at 30 days remaining, and the reference installation's
existing scheduled Uptime workflow fails at 30 days, invalid expiry or missing
publication. A deliberately disabled installation should configure its own
monitoring accordingly; this change does not silently disable reference monitoring.
GitHub may pause scheduled workflows after inactivity, so check that monitoring
continues to run. These checks do not prove a report was received or answered.

At startup, an expired image removes its generated contact file and warns, while
still allowing the app to start. A continuously running container retains its
dated file after expiry; the live monitor is the renewal control. Container restart
or recreation applies changes to publication settings. No automatic expiry renewal
or alteration of the private reporting channel is introduced.

The [RFC 9116 specification](https://www.rfc-editor.org/rfc/rfc9116) defines the
contact format, canonical location and expiry. This file has no OpenPGP signature;
HTTPS and the declared canonical location remain the available authenticity checks.
