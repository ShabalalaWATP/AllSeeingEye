# Cloudflare Radar attack trends

The Cyber icon and Cyber Threat Intelligence overview read one bounded backend
snapshot from `/api/cyber/radar-attacks`. It contains the top ten target billing
countries for Cloudflare Radar Layer 3/4 and Layer 7 attack distributions over
the provider's latest one-day window. Each value is a percentage of the
provider-observed mitigated bytes (Layer 3/4) or requests (Layer 7), not an
incident count or a country's attack rate. The attacked zone's billing country,
when available, determines the target country in the Layer 7 API. It is not a
physical attack coordinate or attacker attribution.

The same server-side `ASE_CLOUDFLARE_RADAR_TOKEN` used for Radar outages has
Radar Read access to both attack endpoints. The token is held only by the
backend, bound to `api.cloudflare.com`, and never included in a URL or API
response. The backend shares a 30-minute cache across users, limits each
provider read to twelve seconds, returns partial or stale results explicitly,
and rate-limits client reads. An administrator can disable the separate
`cloudflare_radar_attack_trends` source without disabling Radar outages.

These figures stay outside the incident store and cyber report counts. Enabling
the Cyber map layer now loads a separate, default-on Cloudflare map sublayer.
Purple country-centre labels show the available Layer 3/4 byte share and Layer 7
request share. Labels are offset from cyber incident context markers, selectable
on the globe and flat map, and can be switched off independently in Cyber
filters. A label is a country reference, not an incident coordinate. The map
only plots countries present in its reference catalogue; the Cyber panel retains
the provider's complete top-ten lists. Cloudflare's network visibility does not
cover all internet traffic. Consult the
[Layer 3 target API](https://developers.cloudflare.com/api/resources/radar/subresources/attacks/subresources/layer3/subresources/top/subresources/locations/methods/target/)
and [Layer 7 target API](https://developers.cloudflare.com/api/resources/radar/subresources/attacks/subresources/layer7/subresources/top/subresources/locations/methods/target/)
for the provider definitions. Cloudflare Radar data is licensed
[CC BY-NC 4.0](https://radar.cloudflare.com/about), so commercial use requires
licence review.
