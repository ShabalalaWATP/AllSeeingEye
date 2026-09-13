# Network connectivity sources

The Network control reads three independently collected source IDs: `ioda_outages`
(IODA warning and critical alerts), `ioda_outage_events` (IODA event windows) and
`cloudflare_radar_outages` (Cloudflare Radar outage annotations). IODA alert and
event records share one parent organisation, so they are not independent
corroboration. Both IODA feeds work without credentials. Radar joins the connector
registry only when `ASE_CLOUDFLARE_RADAR_TOKEN` is set on the server.

Create a Cloudflare token using **Account > Radar > Read**, limited to the intended
account. Keep it in the ignored server `.env` or the host's secret store. Never put
it in frontend configuration. The app sends it only to `api.cloudflare.com` in an
Authorization header. The source inventory reports whether it is configured but
never returns its value. A feed restart is needed after changing the setting.

IODA event collection requests recent country event windows. Cloudflare collection
requests the latest seven days of annotations. Each fetch and the operator snapshot
are bounded. The map places a marker at a country reference only when the provider
explicitly supplied an ISO country code. ASN-only Radar annotations remain in the
list without a map position. The displayed dates are source start times, not
evidence that a disruption is still active. A missing end date is not interpreted
as ongoing. Neither source proves an attack, intentional interference or impact.

Cloudflare states that Radar API data is licensed under
[CC BY-NC 4.0](https://radar.cloudflare.com/about). Attribute Cloudflare Radar
and review licence compatibility before commercial use. IODA is an academic
measurement project; attribute the [IODA data and API](https://ioda.inetintel.cc.gatech.edu/resources).
The [Radar API setup](https://developers.cloudflare.com/radar/get-started/first-request/)
and [outage endpoint](https://developers.cloudflare.com/radar/investigate/outages/)
document the token permission and response format.
