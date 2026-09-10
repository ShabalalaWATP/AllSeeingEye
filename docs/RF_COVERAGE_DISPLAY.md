# RF reach and coverage display

The RF planner offers a **Transmitter → receiver** study and a **360° area**
study for terrain and free-space models. Place a transmitter with the map tool,
choose the radio settings, then explicitly analyse terrain or show the reference
estimate. Selecting an area keeps a saved receiver available for a later link
study but excludes it from the area calculation. A link requires both sites.

The wider RF workspace separates **Configure** and **Results**. Radio/model
settings sit beside transmitter/receiver placement on larger displays and stack
on narrower displays. Advanced antenna and planning inputs remain in disclosures.
Analysis runs only when requested; completed output opens Results. Edit study
returns to the setup, with changed inputs invalidating the previous result.

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
table shows why. Reduce the sampling radius to assess closer targets; do not
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
over 200 km. The cap increases spacing on longer paths. Radial studies retain
**409 positions**, 24 bearings and 17 outward steps within 50 km. Quadratic spacing
puts more points near TX: at 50 km the first assessed target is about 692 m,
previously 5.88 km. Reducing survey radius further resolves closer targets.
The first target needs at least one intermediate terrain sample.

Results show the largest sampling interval, nominal DEM grid spacing and first
assessed radial distance. Sampling more frequently does not improve the underlying
zoom-10 DEM or prove narrow ridges are resolved. Neither spacing value is a height
accuracy guarantee. Negative elevations are retained and flagged because source
bathymetry can differ from the actual water surface.

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
