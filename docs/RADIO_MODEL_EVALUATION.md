# Radio modelling and terrain evidence

The map has a sampled terrain/Fresnel radio screen and a separate native NTIA
LFMF groundwave adapter. The general terrain tool reuses the bounded elevation
sampler for profiles and geometric ground visibility. It does not use the radio
model to decide visibility.

## ITM evaluation

The [official NTIA Irregular Terrain Model repository](https://github.com/NTIA/itm)
provides the maintained C++ implementation, model input definitions, error and
warning codes, and example input/output files. The published frequency range is
20 MHz to 20 GHz. Its introductory attenuation description applies to distances
greater than 1 km. Model validity must be checked against the complete documented
input constraints, rather than inferred from these two headline limits.

ITM is a useful candidate for a separate terrain-based propagation mode. It must
not be presented as an accuracy upgrade to every existing RF study. It uses
additional environmental and statistical assumptions, and model output still
depends on the quality of supplied terrain and site data.

The repository supplies point-to-point and area example cases. NTIA explicitly
says these are not a comprehensive validation set. Passing those examples would
establish agreement with selected reference outputs, not field accuracy.

No ITM native adapter or new binary dependency is installed. The existing
groundwave adapter lazily imports `ITS.Propagation.LFMF`. That boundary provides a
useful architectural pattern, but does not establish compatibility with ITM or
provide its input model.

Before enabling ITM:

1. Select and pin an official source revision and a maintained binding, or build
   a minimal owned binding. Review the licence, provenance, build instructions
   and redistribution terms. Do not download a platform DLL at request time.
2. Establish reproducible builds for the supported Windows, macOS and Linux
   environments and container runtime. Check the ABI, numerical behaviour,
   supported architectures and unavailable-library behaviour.
3. Define a propagation port with explicit terrain profile spacing, terminal
   heights, frequency, polarisation, electrical properties, radio climate,
   refractivity and variability inputs. Do not silently guess missing inputs.
4. Map every native error and warning to structured results. Retain the input
   assumptions, terrain attribution and model revision in saved studies and
   exports. Missing terrain must remain an unavailable analysis.
5. Run the published point-to-point and area example cases, then independent
   edge and invalid-input tests. Check the profile encoding, unit conversions,
   statistical interpretation and antenna/power budget normalisation.
6. Bound samples, native execution time, concurrent work and queue length. A
   timed-out native call must not release its capacity while it still runs.
   Isolate the native worker if cancellation cannot safely stop it.
7. Compare representative results with an independently maintained reference
   implementation and appropriately licensed measured paths. Report the tested
   domains and limitations rather than a general accuracy claim.

This integration should be delivered separately from UI improvements so that
saved-study behaviour and propagation validation can be assessed independently.

## Terrain evidence

The elevation service uses Mapzen Terrain Tiles at zoom 10 and returns provider
attribution, nominal resolution and limitations. Denser request samples cannot
recover ground details absent from the source raster. The source has mixed data
provenance; consult its [attribution](https://github.com/tilezen/joerd/blob/master/docs/attribution.md).

The standalone profile preserves negative elevations. Ground visibility treats
negative terrain as ambiguous because it may represent land below sea level or
bathymetry. It does not invent a water surface. Missing elevations and unknown
intermediate terrain cannot produce a passing visibility result.

Visibility is calculated only at marked ground samples along 24 directions. It
accounts for spherical Earth curvature, without refraction, buildings or trees.
The spaces between samples remain unassessed. A later higher hillside can become
visible beyond a hidden lower point. This is not a radio coverage estimate.

Higher-resolution terrain needs a separate provider and operations decision:

- Identify coverage, horizontal and vertical reference systems, acquisition
  dates, void handling, licence, attribution and distribution limits.
- Expose source choice and actual provenance through the terrain gateway. Do
  not disguise fallback to a coarser provider as the requested resolution.
- Budget requests, cache size, concurrency and memory independently of display
  zoom. Recheck SSRF restrictions if a new host or URL template is introduced.
- Test coastal and below-sea-level cases, missing tiles, high latitudes,
  antimeridian paths, inconsistent source heights and provider failures.
- Distinguish ground models from surface models that include buildings or
  vegetation. Finer pixel spacing alone is not proof of better height accuracy.

No higher-resolution provider, land-cover source or building-height dataset is
configured by this feature. These remain explicit follow-up integrations.
