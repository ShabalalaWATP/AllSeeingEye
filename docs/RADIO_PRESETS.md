# Radio preset catalogue

Updated 9 September 2026. Open the map's radio link planner and use **Radio preset**.
The 25 choices are grouped into Bowman scenarios, other military radios and general
radio examples, with a separate custom option. Previous preset IDs remain valid.

## Bowman scenarios

| Preset | Selected planning inputs | Model |
| --- | --- | --- |
| Bowman VHF manpack | 60 MHz, 5 W, 2 m antennas | Terrain |
| Bowman VHF vehicle | 60 MHz, 50 W, 3 m transmit / 2 m receive antenna | Terrain |
| Bowman PRC325 HF | 7 MHz, 20 W, 3 m antennas | HF groundwave |
| Bowman PRC325 NVIS | 5 MHz, 60–90 degree assumed launch angles | HF skywave scenario |

These are explicitly labelled illustrative configurations. The
[Parliamentary reference](https://hansard.parliament.uk/Commons/2005-03-02/debates/a9d8af13-2718-4f0c-86c0-bbf5e3f9f31f/BowmanSystem)
identifies the PRC325 HF manpack. The
[Cooper antenna catalogue](https://www.cooperantennas.com/airborne-antennas.php)
documents Bowman-compatible 30–88 MHz antennas. Neither establishes exact
PRC355/356 or VRC357/358/359 transmitter settings. The selected powers are assumptions,
not claimed Bowman variant specifications. Other manufacturers' base/export radio
data is not silently relabelled as Bowman data.

## Other military equipment

Published bands/powers appear alongside the selected preset and its source link.
All selected frequencies, heights, gains, losses and receiver sensitivities remain
editable planning assumptions. Ratings apply to the named model and stated mode.

| Family | Choices included | Public source |
| --- | --- | --- |
| Harris AN/PRC-150(C) | HF 20 W PEP at 7 MHz; VHF FM 10 W at 50 MHz | [Manufacturer brochure, government-hosted copy](https://www.zsis.hr/UserDocsImages/Sigurnost/pdfs/AN_PRC-150.pdf) |
| L3Harris AN/PRC-152A | Terrestrial VHF 60 MHz / UHF 350 MHz, each 5 W | [Manufacturer datasheet](https://www.l3harris.com/sites/default/files/2021-01/cs-tcom-falcon-iii-an-prc-152a-wideband-networking-handheld-radio-datasheet.pdf) |
| L3Harris AN/PRC-117G | Narrowband terrestrial 150 MHz, 10 W | [Manufacturer datasheet](https://www.l3harris.com/sites/default/files/2021-01/cs-tcom-an-prc-117g-multiband-networking-manpack-radio-datasheet.pdf) |
| Thales AN/PRC-148 JEM / MBITR | Handheld FM 150 MHz, 5 W | [Manufacturer brochure](https://www.thalesdsi.com/wp-content/uploads/2018/05/MBITR.pdf) |
| SINCGARS RT-1702 | 60 MHz manpack 5 W; vehicle 50 W with external RFPA | [Manufacturer datasheet](https://www.l3harris.com/sites/default/files/2021-01/cs-tcom-sincgars-rt-1702-vhf-combat-net-radio-datasheet.pdf) |
| Harris RF-5800H-MP | Existing HF 7 MHz, 20 W PEP example retained | [Archived manufacturer DS-211H](https://w2hx.com/x/Harris/RF-5800/Docs/5800H_MP.pdf) |

AN/PRC-150(C) has separate PEP and FM ratings. PEP is peak envelope power, not
average speech power. The PRC-152A terrestrial presets do not use its 10 W SATCOM
burst rating. The PRC-117G preset uses the unambiguous 30–512 MHz narrowband / 10 W
specification, not its wideband peak or SATCOM rating. Its datasheet's wideband
frequency row has a unit typo, so that row is not used. The RT-1702 50 W choice
requires its external amplifier; it is not the bare radio's rating or an RT-1523 rating.

## Behaviour and limits

Selection fills the existing calculator. HF choices select groundwave/skywave and
VHF/UHF choices select terrain, while an explicit free-space selection is retained.
Environmental edits survive preset changes; the NVIS preset supplies its launch
angles. Selection clears old results and requires an explicit new analysis. Editing
a radio input changes the selection to Custom and removes equipment-specific claims.

Existing terrain, groundwave and skywave limitations remain. These presets do not
add waveform, encryption, hopping, network-throughput or satellite-link simulation.
Skywave is geometric and does not use transmit power to calculate received signal.
There are no operational network frequencies, new remote requests, credentials,
dependencies, API changes or database changes in this delivery.

## Verification

59 focused tests passed across presets, RF calculations, power inputs, model controls,
analysis and map integration. A 22-test coverage run measured the extracted chooser
at 100% statements/lines/functions and 90% branches. Typecheck and production build
passed. Static source review found no unresolved rating or interaction issue.
The existing local browser policy prevents an interactive/GPU check; the tests use
the existing component and map doubles. Provider references were researched separately
from deterministic tests.
