# RF reach and coverage display

The RF planner offers a **Transmitter → receiver** study and a **360° area**
study for terrain and free-space models. Place a transmitter with the map tool,
choose the radio settings, then select **Analyse** or show the reference
estimate. Selecting an area keeps a saved receiver available for a later link
study but excludes it from the area calculation. A link requires both sites.

The compact RF workspace separates **Configure** and **Results**. The panel is
capped at 360 px, with radio/model settings above transmitter/receiver placement
to leave more of the map visible. **Transmit power (watts)** appears first in
Configure. Skywave shows the saved power as disabled with an explanation, since
that mode estimates geometry rather than received power. Model, environment and
engineering overrides remain under **Advanced**. An explicit analysis opens Results
when complete; an automatic update preserves the selected tab. Edit study
returns to the setup, with changed inputs invalidating the previous result.

## Automatic setup and updates

New studies start with automatic model and area selection. VHF/UHF uses the
terrain screen; HF uses groundwave unless the selected preset describes a skywave
scenario. Customising a skywave preset retains that HF choice, even if frequency
temporarily moves into VHF/UHF and later returns. A manually selected model
overrides this choice. Frequency alone does
not determine the real propagation mechanism. Preset assumptions remain visible
and editable, including ground properties and skywave geometry.

A receiver link uses the actual distance between sites and does not ask for an
area radius. For an area study, the terrain search extent starts from the ideal
link budget and radio horizon with search headroom, bounded to 1 to 50 km. The
initial extent is reduced if needed to fit the existing terrain tile/latitude
limits. HF groundwave uses a bounded 200 km curve in automatic area mode. These
extents define where the model checks, not the distance reception is guaranteed.
Manual mode labels the setting **Area to analyse (km from transmitter)**.

An automatic terrain area can make **one additional pass**: wider when passing
targets reach its edge, or closer when only nearby targets pass. Missing terrain
and possible bathymetry prevent refinement. The final screen retains both
passes' sampled evidence inside the final extent. A failed or inconsistent
second pass leaves the initial result with a warning. It never triggers a third
pass or retries automatically.

**Auto update** is enabled initially, but only becomes active after the first
explicit Analyse action in that panel session. Valid input/site edits then
schedule one analysis after a 1.2-second debounce, at least 30 seconds after the
last manual or automatic attempt. Invalid inputs, site picking and an in-flight
study pause scheduling. Identical failed inputs are not retried in a loop.
Turning it off cancels pending automatic work while retaining completed results.
Clear analysis, closing the panel, or changing account/access disarms automation.
There is no mount-time analysis, polling or background job.

The panel reuses at most two complete elevation batches with exactly matching
positions for up to five minutes from fetch. Radio-only changes can reuse that
terrain. The cache is memory-only and clears on account, role, active-state,
workspace-access changes and unmount. Cancelled responses cannot refill it.

In the area study, **Show estimated coverage bubble** shades the footprint.
This switch only changes rendering of the saved result. It makes no new terrain
request, does not discard the analysis and adds no animation or polling. Moving
a site or changing study/radio inputs invalidates the previous result. Planning
positions, analysis and shading preference clear with workspace access changes.

## Reading a terrain result

| Mark                            | Meaning                                                      |
| ------------------------------- | ------------------------------------------------------------ |
| Mint line                       | Sampled clearance, subject to the model limits               |
| Amber line / stop               | Fresnel clearance restriction or insufficient planning reserve |
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
table shows why. Reduce the manual analysis area to assess closer targets; do not
interpret the absence of a passing screen as proof of zero reception.

## Reading a free-space reference

The boundary is the smaller of the ideal distance meeting sensitivity plus the
selected planning reserve and the
smooth-Earth radio horizon. Its label identifies which limits the radius. A
receiver path beyond it turns red at the calculated geodesic boundary; both the
boundary and receiver have distance labels. **Red here means beyond the ideal
model limit, not a measured obstruction.** Terrain has not been checked.

The optional shaded reference circle and inner rings are static. Dateline
geometry is kept continuous. A fill enclosing a pole is omitted rather than
projected into the wrong hemisphere; the globe retains the outline. Flat-map
geometry is clipped conservatively at the Web Mercator latitude limit.

## Planning assumptions and data quality

The UI starts with a **10 dB planning reserve**, editable from 0 to 60 dB.
This is an allowance above receiver sensitivity, not measured fading or a
calibrated reliability percentage. Raw received power and raw margin remain
unchanged by reserve; remaining planning margin subtracts it. Terrain clearance
and sufficient remaining margin are both required for a passing screen. Free-space
and HF groundwave boundaries use the same reserve criterion. HF skywave remains
geometry only. Use the receiver sensitivity appropriate to bandwidth, modulation
and required performance, rather than assuming one equipment figure fits all modes.

The effective Earth factor is editable for terrain and free-space scenarios;
the default is k = 4/3. Terrain additionally accepts a uniform assumed obstacle
height at intermediate samples. It does not alter DEM values or endpoint mast
elevations. The profile distinguishes this assumed screen from source ground.
It is not a detected building/vegetation inventory or a material-loss model.

Point-to-point sampling targets intervals of about 100 m, capped at **769 points**
over 200 km. The cap increases spacing on longer paths. Each radial pass uses
**409 positions**, 24 bearings and 17 outward steps within 50 km. The optional
second pass combines at most **817 unique positions**, with at most 35 points
per bearing including TX. Each network request remains capped at 409 positions.
Quadratic spacing
puts more points near TX: at 50 km the first assessed target is about 692 m,
previously 5.88 km. Reducing survey radius further resolves closer targets.
The first target needs at least one intermediate terrain sample.

Results show the largest sampling interval, nominal DEM grid spacing and first
assessed radial distance. Sampling more frequently does not improve the underlying
zoom-10 DEM or prove narrow ridges are resolved. Neither spacing value is a height
accuracy guarantee. Negative elevations are retained and flagged because source
bathymetry can differ from the actual water surface.

For a receiver link, an automatic improvement check can rescreen the same DEM
with a higher TX or RX mast and report the smaller one-site height change that
clears the sampled Fresnel screen. It reports the resulting planning margin,
including a remaining power shortfall. A clear but weak path instead reports
the missing margin. These are local what-if calculations, never applied to the
inputs automatically. Uncertain terrain suppresses this advice. A calculated
height can be impractical and still requires a site/equipment feasibility check.

## Limits and verification

Provider intake bounds remain 1,000 positions, 64 unique tiles and a 64 KiB body.
There are no new credentials, endpoints, dependencies or
background jobs. RF layers do not intercept map clicks. See
[map tools and model assumptions](MAP_TOOLS_AND_LAYERS.md) and
[equipment presets](RADIO_PRESETS.md).

The sampled diffraction screen is not a complete
[ITU-R P.526 model](https://www.itu.int/rec/R-REC-P.526/en) or a measured reception
map. Coarse samples can miss ridges, vegetation and buildings. Missing terrain
does not become flat ground or a passing screen.

A full terrain propagation model such as [NTIA ITM](https://github.com/NTIA/itm)
would be a separate validated integration, requiring climate, ground electrical
properties, refractivity, polarisation and variability assumptions. The current
single dominant edge screen does not model multiple-edge diffraction, detailed
antenna patterns, measured noise/interference or live atmospheric conditions.
Useful planning should be followed by site checks and measurements.

Automated regressions cover range-boundary placement, ray obstruction and
uncertainty, study selection, display-only shading, retained site positions,
access invalidation, static geometry bounds and both projection settings.
Interactive browser/GPU acceptance remains unverified under the existing
administrator browser-control policy.
