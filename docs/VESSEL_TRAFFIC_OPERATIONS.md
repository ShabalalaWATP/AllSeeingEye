# Regional vessel positions

The `digitraffic_ais` connector reads Fintraffic's open AIS location API for
Finnish waterways. It joins the default connector registry when the application
starts normally; feed collection must be enabled. No account or API key is
required. This is regional coverage. It does not implement worldwide satellite
AIS, vessel histories, ship-name lookup or ownership verification.

Both globe and flat map use `vessel_position` events. The vessel switch controls
display; the maritime category filter also applies. Directional boat symbols use
reported heading, falling back to course over ground. A side-view symbol means
direction is unavailable. At low zoom, the existing bounded traffic sample stays
visible while other positions contribute to clusters.

## Collection and freshness

The connector queries the previous 15 minutes every two minutes. API `from`/`to`
parameters and `timestampExternal` use epoch milliseconds. The separate AIS
`timestamp` field is a seconds/status code and is never treated as an epoch.
The inspector labels the date as position-record time. Retrieval remains
separate. MMSI is a reported identifier, not confirmed vessel identity.

Only finite, valid point coordinates are mapped; AIS unavailable coordinates do
not become `(0,0)`. Valid zero coordinates remain valid. Unavailable speed,
course and heading values remain unknown. Duplicate MMSIs retain the newest
record in a batch. Fresh timestamps change the content hash even for stationary
vessels. Older reports and reports more than 30 seconds in the future are excluded.

Vessel records expire on periodic cleanup once their position-record time is
more than 15 minutes old. Retrieval cannot prolong an old position. Source
failures retain existing records until that expiry, and existing SSE expiry
messages remove them from connected clients. NAVAREA and other maritime warnings
retain their normal six-hour window. The shared live store remains bounded and
does not archive vessel tracks.

## Controls, limits and attribution

Administration source enable/disable, health and reset controls apply. Set
`ASE_FEEDS_DISABLED=digitraffic_ais` to exclude it at startup. No migration or
secret configuration is needed. The dedicated HTTP client sends fixed
application identification without operator contact details, requests required
gzip, preserves DNS pinning, disables redirects and is closed with the container.

Each response is limited to 5 MiB compressed, 5 MiB decoded and 5,000 location
records. Gzip decoding limits output during decompression and rejects truncated,
concatenated or trailing streams. Invalid batch structure causes a source-health
failure rather than a silent partial result. The two-minute interval remains
below the documented unauthenticated request limit. No map pan or user click
triggers another provider request.

Source: [Fintraffic / Digitraffic](https://www.digitraffic.fi/en/marine-traffic/),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Data is normalised and
freshness-filtered. Attribution, licence URL, source URL and modifications are
present in each event and retained when that evidence is frozen into a report.
The overlay panel also links the source and licence. Preserve attribution and
disclaimers when redistributing outputs. Positions may be missing, delayed,
incorrect or spoofed and are not navigation advice.

Technical references: [OpenAPI](https://meri.digitraffic.fi/swagger/openapi.json),
[API instructions](https://www.digitraffic.fi/en/support/instructions/) and
[data terms](https://www.digitraffic.fi/en/terms-of-service/), checked 7 September 2026.

## Acceptance and remaining work

One bounded real request through the implemented client accepted 681 fresh
positions on 7 September 2026. Only the count was recorded; raw positions were
not retained. This proves a successful response/parser combination at that time,
not continual availability or completeness. Synthetic tests cover timestamps,
sentinels, gzip limits, duplicate records, stationary updates, outage expiry and
SSE delivery. Actual GPU/browser visual acceptance remains outstanding.

Wider provider coverage and credential onboarding remain open. Large expiry
batches now trigger [live-stream recovery](LIVE_STREAM_RECOVERY.md) instead of
truncated removal notices. The per-response AIS cap remains 5,000.
