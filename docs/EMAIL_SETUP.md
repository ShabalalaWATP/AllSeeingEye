# Set up account email

The app sends activation links, password reset links and email MFA codes through
SMTP. A sending service and a verified sender are required. The app already
contains the SMTP integration; no additional package is needed.

## Recommended starting point: Resend

Resend supports the app's existing SMTP transport. Its free transactional plan
currently allows 3,000 emails per month, with a limit of 100 per day. Check the
[current pricing](https://resend.com/pricing) before choosing a plan. These limits
were checked on 21 September 2026.

1. Create a Resend account and open **Domains**.
2. Add a sending subdomain you control, such as `notify.example.com`.
3. Add the exact DNS records shown by Resend at your DNS provider. Wait for Resend
   to show the domain as **Verified**. Keep existing website and mailbox records;
   do not replace them with guessed records. See the
   [domain guide](https://resend.com/docs/dashboard/domains/introduction).
4. Keep open and click tracking disabled for account and password-reset messages.
5. Create an API key with sending permission restricted to that domain. Store it
   privately. See [API key management](https://resend.com/docs/dashboard/api-keys/introduction).
6. Put the following settings in the private environment file used by the API,
   replacing the key and sender with your values:

```dotenv
ASE_SMTP_HOST=smtp.resend.com
ASE_SMTP_PORT=465
ASE_SMTP_SECURITY=tls
ASE_SMTP_USERNAME=resend
ASE_SMTP_PASSWORD=REPLACE_WITH_YOUR_RESEND_API_KEY
ASE_SMTP_FROM_EMAIL=noreply@notify.example.com
```

The SMTP password is the Resend API key. These values follow the
[Resend SMTP documentation](https://resend.com/docs/send-with-smtp). A separate
mailbox is not required for the verified sending address. Receiving replies is
a separate service.

## Apply the settings

For the repository's standard Docker Compose setup, edit the root `.env` file
on the machine running the app. From that directory, recreate the API service:

```sh
docker compose up -d --no-deps --force-recreate api
docker compose ps api
```

If your deployment uses extra Compose files, a named project or a different
environment-file path, use those same deployment options with this command.
Do not start a second stack with different options. A plain container restart
does not load changed Compose environment values. The API briefly restarts;
the database and web service do not need to be recreated for SMTP settings.

For a local backend, put the settings in `backend/.env` and restart the backend
process. Confirm `ASE_PUBLIC_BASE_URL` is the browser-facing app URL so links
point to the right installation.

## Verify delivery

1. Open **Forgot password** and enter the email of your own existing account.
2. Check Resend's email list for the send result, then check your inbox and spam.
3. Confirm the link points to the correct app. Completing the reset changes the
   password and signs out existing sessions, so use a test account for a full
   end-to-end check when possible.
4. Verify email MFA separately with a test account before relying on it for access.

The catalogue can show that SMTP is configured. That does not prove that the
provider accepted a message or that it reached the recipient's inbox.

| Symptom | Check |
|---|---|
| Email recovery unavailable | Both host and sender must be configured, and the API must load the updated environment. |
| Authentication rejected | Username must be `resend`; password must be the API key, not the account password. Check key permission and domain restriction. |
| Sender rejected | The sending domain must be verified and match the configured sender. |
| Connection timeout | Check outbound access to port 465. Resend also supports port 587 with `ASE_SMTP_SECURITY=starttls`. |
| Provider accepts mail but no inbox message | Check spam, recipient suppression/bounces, domain authentication and provider quotas. |
| Reset link opens the wrong site | Correct `ASE_PUBLIC_BASE_URL` and recreate/restart the API. |

Keep real keys in the private environment file, outside Git. Avoid commands such
as `docker compose config` in shared logs because they can print resolved secrets.
Without working email, an administrator can issue a password reset link from
**Administration > Users** after verifying the requester's identity. This does
not bypass MFA.

## Other providers

Any SMTP service that supports certificate-verified STARTTLS or implicit TLS can
be configured through the same settings. Use the provider's exact SMTP host,
credentials and verified sender. Port 587 usually pairs with `starttls`; port 465
pairs with `tls`. Both host/sender and username/password must be configured in
pairs. The application does not support sending credentials over plaintext SMTP.
