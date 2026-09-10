# RF reach and coverage display

The RF planner offers a **Transmitter → receiver** study and a **360° area**
study for terrain and free-space models. Place a transmitter with the map tool,
choose the radio settings, then explicitly analyse terrain or show the reference
estimate. Selecting an area keeps a saved receiver available for a later link
study but excludes it from the area calculation. A link requires both sites.

In the area study, **Show estimated coverage bubble** shades the footprint.
This switch only changes rendering of the saved result. It makes no new terrain
request, does not discard the analysis and adds no animation or polling. Moving
a site or changing study/radio inputs invalidates the previous result. Planning
positions, analysis and shading preference clear with workspace access changes.

## Reading a terrain result

| Mark                            | Meaning                                                      |
| ------------------------------- | ------------------------------------------------------------ |
| Mint line                       | Sampled clearance, subject to the model limits               |
| Amber line / stop               | Fresnel clearance restriction or insufficient modelled power |
| Red line / cross                | Obstructed direct ray, not proof of zero reception           |
| Grey broken tail / unknown mark | Missing terrain or an unassessed part of the survey          |
| Labelled survey ring            | Requested analysis extent, not the maximum reception range   |

Dark underlays make the coloured paths visible over imagery. TX, RX, the first
sampled intrusion and selected radial targets have distance labels. A small RF
readout keeps an expandable key available when the calculator panel is closed.
The profile chart uses the same palette and obstruction position as the map.

For a receiver link, the first sampled obstruction is labelled by distance from
TX. The preceding sample interval is amber because the actual intrusion may start
between samples. The direct ray remains red afterwards even if later local terrain
is below that ray. This describes the line between those two antenna elevations;
it does not infer coverage for other receiver heights. Diffraction may carry a
signal despite an obstructed direct ray. Power shortfalls are reported separately.

For an area, each of the 24 bearings stops at its first failing or unknown receiver
target. The results table gives the last passing target and the first stop or
survey limit for every bearing. A failing target is not the location of the ridge
that obstructed it. The map has at most three radial callouts to limit clutter;
all assessed points and stops retain their status marks.

The optional bubble interpolates only to the shorter passing distance of adjacent
bearings. A direction with no passing target or unknown terrain leaves a gap.
The shaded area between rays is illustrative, not terrain-verified coverage.
The distinct narrow sampled sectors and grey unassessed tails remain visible.
If no adjacent directions have passing targets, no bubble is drawn. The results
table shows why. Reduce the sampling radius to assess closer targets; do not
interpret the absence of a passing screen as proof of zero reception.

## Reading a free-space reference

The boundary is the smaller of the ideal receiver-sensitivity distance and the
smooth-Earth radio horizon. Its label identifies which limits the radius. A
receiver path beyond it turns red at the calculated geodesic boundary; both the
boundary and receiver have distance labels. **Red here means beyond the ideal
model limit, not a measured obstruction.** Terrain has not been checked.

The optional shaded reference circle and inner rings are static. Dateline
geometry is kept continuous. A fill enclosing a pole is omitted rather than
projected into the wrong hemisphere; the globe retains the outline. Flat-map
geometry is clipped conservatively at the Web Mercator latitude limit.

## Limits and verification

The propagation calculations, providers and capacity bounds are unchanged:
up to 129 path samples over 200 km, or 409 positions across 24 bearings within
50 km for terrain. There are no new credentials, endpoints, dependencies or
background jobs. RF layers do not intercept map clicks. See
[map tools and model assumptions](MAP_TOOLS_AND_LAYERS.md) and
[equipment presets](RADIO_PRESETS.md).

The sampled diffraction screen is not a complete
[ITU-R P.526 model](https://www.itu.int/rec/R-REC-P.526/en) or a measured reception
map. Coarse samples can miss ridges, vegetation and buildings. Missing terrain
does not become flat ground or a passing screen.

Automated regressions cover range-boundary placement, ray obstruction and
uncertainty, study selection, display-only shading, retained site positions,
access invalidation, static geometry bounds and both projection settings.
Interactive browser/GPU acceptance remains unverified under the existing
administrator browser-control policy.
