# HF groundwave implementation

The authenticated `POST /api/radio/groundwave` endpoint runs the official NTIA
LFMF native model locally through `proplib-lfmf==1.1.0`. It performs no network
requests. This is a homogeneous smooth-earth propagation calculation, separate
from the app's terrain sampling and HF skywave planning tools.

## Provenance and reproducibility

- [NTIA Python wrapper](https://github.com/NTIA/LFMF-python) links the verified
  [PyPI distribution](https://pypi.org/project/proplib-lfmf/1.1.0/).
- Native model: [NTIA/LFMF v1.1](https://github.com/NTIA/LFMF/tree/57886e9d0a29fd8f04a6416dc3f782322f5a3589),
  commit `57886e9d0a29fd8f04a6416dc3f782322f5a3589`.
- The universal Python wheel bundles native libraries for supported platforms.
  Its locked SHA-256 is
  `84b047b771a5b6ad705af9bd643b718fe09e2faad7c631786e12de02ad4dbff7`.
- [ITU-R P.368-10](https://www.itu.int/rec/R-REC-P.368-10-202208-I/en)
  describes the groundwave method. The
  [ITU software catalogue](https://www.itu.int/en/ITU-R/study-groups/rsg3/rwp3m/Pages/digprod.aspx)
  identifies LFMF-smoothEarth as integral software for P.368. ASE uses NTIA's
  maintained v1.1 implementation, not the older GRWAVE executable.
- NTIA's worldwide royalty-free redistribution permission and attribution
  terms are retained in [the licence](licenses/NTIA_LFMF_LICENSE.md).
  NTIA supplies the software without warranties. ASE does not modify its solver.

## Inputs and interpretation

ASE limits this study to 1.6 to 30 MHz, vertical polarisation, antenna heights
0 to 50 metres above ground, relative permittivity 1 to 100, conductivity
0.00001 to 10 S/m and surface refractivity 250 to 400 N-units. Source bounds are
wider in frequency and distance; these narrower application limits are explicit.
Heights are above local ground, not elevation above sea level.

The endpoint calculates 2 to 64 logarithmically spaced samples from 1 km to the
requested maximum, between 2 and 200 km. Starting at 1 km keeps the study beyond two
wavelengths at its minimum frequency. Each sample reports native basic
transmission loss and the solution method (flat-earth curve or residue series).

The native reference electric field uses the requested antenna-input watts and
the model's 4.77 dBi transmitting antenna. It is explicitly named
`native_reference_field_dbuv_m`; user gains and losses do not alter this column.
Received power is calculated separately as:

`30 + 10 log10(tx_power_w) + tx_gain_dbi + rx_gain_dbi - system_loss_db - basic_loss_db`

This avoids silently applying the native model's fixed gains to a different
antenna. Conductivity and permittivity describe the entire assumed homogeneous
surface. They are operator inputs, not measured location-specific data.

The model does not include irregular terrain, clutter, mixed land/sea segments,
skywave, antenna efficiency estimates, environmental noise or fading. A receiver
sensitivity crossing can support an assumed homogeneous-ground map contour; it
is not a measured service boundary or a guarantee of intelligible communication.
Do not extrapolate beyond the requested curve or below its 1 km start.

The RF workspace applies an explicit planning reserve to its reception threshold,
defaulting to 10 dB above the chosen receiver sensitivity. The reserve changes
which model samples pass, not their predicted received power. Results retain
both raw and remaining margin, with separate sensitivity and planning-threshold
lines on the chart. A contour ends at the last consecutive passing sample before
the first failure; it does not bridge isolated later passing samples. The reserve
is a user assumption, not a computed noise level or statistical reliability.

## Capacity and failure behaviour

The API authenticates before parsing a maximum 4 KiB JSON body, validates finite
bounded values, and rechecks the session after calculation. Responses are
`private, no-store`. It allows six requests per user per minute and one native
worker at a time per API process, with no waiting queue. Calculation runs off the
event loop. The five-second response timeout does not release the worker slot
until native execution really finishes, preventing timed-out requests from
accumulating background work. Cancellation has the same property.

Native import or calculation failures return an explicit failure. ASE does not
replace them with a made-up range. No coordinates or raw study inputs are logged
or persisted by this feature.

## Validation

The Windows x64 bundled library executed successfully. Tests compare five
published [NTIA reference cases](https://github.com/NTIA/LFMF-test-data/blob/c593360c1c9f1cde463d98a3bf89447903d95861/LFMF_Examples.csv)
at their published 0.1 dB precision. Additional tests cover the HF adapter's gain,
power and loss normalisation, model bounds, authentication, session revocation,
bounded request bodies and capacity retention after timeout or cancellation.
The focused suite passed 21 tests with 100% statement and branch coverage across
the five changed groundwave implementation modules. Scoped Ruff and Bandit,
the full backend type check and both architecture contracts passed.

A warmed local 64-sample study at 7 MHz ran in a median 1.013 ms across 20 runs
(maximum 1.239 ms). A 36-case frequency/height/conductivity/permittivity boundary
matrix, each with 64 samples, completed in 131.44 ms including initial loading.
These are local solver timings, not end-to-end API or rendering guarantees.
