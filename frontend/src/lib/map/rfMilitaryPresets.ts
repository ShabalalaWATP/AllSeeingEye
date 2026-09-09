import { DEFAULT_RF_INPUTS } from './rfPlanning';
import type { RfPreset } from './rfPresetTypes';

const PORTABLE = {
  ...DEFAULT_RF_INPUTS,
  transmitHeightM: 1.5,
  receiveHeightM: 1.5,
  transmitGainDbi: 0,
  receiveGainDbi: 0,
  sensitivityDbm: -110,
  distanceKm: 5,
};
const PRC150 = 'https://www.zsis.hr/UserDocsImages/Sigurnost/pdfs/AN_PRC-150.pdf';
const PRC152 =
  'https://www.l3harris.com/sites/default/files/2021-01/cs-tcom-falcon-iii-an-prc-152a-wideband-networking-handheld-radio-datasheet.pdf';
const PRC117 =
  'https://www.l3harris.com/sites/default/files/2021-01/cs-tcom-an-prc-117g-multiband-networking-manpack-radio-datasheet.pdf';
const PRC148 = 'https://www.thalesdsi.com/wp-content/uploads/2018/05/MBITR.pdf';
const SINCGARS =
  'https://www.l3harris.com/sites/default/files/2021-01/cs-tcom-sincgars-rt-1702-vhf-combat-net-radio-datasheet.pdf';

/** Public product data checked September 2026. Selected frequencies and geometry are examples. */
export const RF_MILITARY_PRESETS: readonly RfPreset[] = [
  {
    id: 'prc150-hf',
    group: 'military',
    basis: 'published',
    label: 'Harris AN/PRC-150(C) · HF 20 W PEP',
    propagation: 'hf-groundwave',
    specification: { band: '1.6–59.999 MHz', output: '1 / 5 / 20 W PEP; FM 1 / 5 / 10 W' },
    note: 'Uses the published 20 W PEP setting at an illustrative 7 MHz. PEP is peak envelope power, not average speech power. This is the AN/PRC-150(C), not a Bowman variant.',
    referenceUrl: PRC150,
    referenceLabel: 'Harris AN/PRC-150(C) datasheet (government-hosted copy)',
    values: {
      ...PORTABLE,
      frequencyMHz: 7,
      transmitDbm: 30 + 10 * Math.log10(20),
      transmitHeightM: 3,
      receiveHeightM: 3,
      distanceKm: 20,
    },
  },
  {
    id: 'prc150-vhf',
    group: 'military',
    basis: 'published',
    label: 'Harris AN/PRC-150(C) · VHF FM 10 W',
    propagation: 'terrain',
    specification: { band: '1.6–59.999 MHz; selected VHF FM example', output: 'FM: 1 / 5 / 10 W' },
    note: 'Uses the documented FM power setting at an illustrative 50 MHz. The HF 20 W PEP rating is not applied to this FM scenario.',
    referenceUrl: PRC150,
    referenceLabel: 'Harris AN/PRC-150(C) datasheet (government-hosted copy)',
    values: { ...PORTABLE, frequencyMHz: 50, transmitDbm: 40 },
  },
  {
    id: 'prc152a-vhf',
    group: 'military',
    basis: 'published',
    label: 'L3Harris AN/PRC-152A · VHF 5 W',
    propagation: 'terrain',
    specification: {
      band: '30–520 MHz and 762–870 MHz',
      output: '0.25–5 W; 10 W SATCOM burst separately',
    },
    note: 'Illustrative terrestrial FM link at 60 MHz using the 5 W setting. Satellite access and SATCOM burst power are not modelled.',
    referenceUrl: PRC152,
    referenceLabel: 'L3Harris AN/PRC-152A datasheet',
    values: { ...PORTABLE, frequencyMHz: 60, transmitDbm: 30 + 10 * Math.log10(5) },
  },
  {
    id: 'prc152a-uhf',
    group: 'military',
    basis: 'published',
    label: 'L3Harris AN/PRC-152A · UHF 5 W',
    propagation: 'terrain',
    specification: {
      band: '30–520 MHz and 762–870 MHz',
      output: '0.25–5 W; 10 W SATCOM burst separately',
    },
    note: 'Illustrative terrestrial FM link at 350 MHz using 5 W. This does not simulate SATCOM, networking throughput or hopping.',
    referenceUrl: PRC152,
    referenceLabel: 'L3Harris AN/PRC-152A datasheet',
    values: { ...PORTABLE, frequencyMHz: 350, transmitDbm: 30 + 10 * Math.log10(5) },
  },
  {
    id: 'prc117g-narrowband',
    group: 'military',
    basis: 'published',
    label: 'L3Harris AN/PRC-117G · narrowband 10 W',
    propagation: 'terrain',
    specification: {
      band: '30–512 MHz narrowband; 30–2000 MHz overall',
      output: '10 W narrowband; wideband has separate peak/average ratings',
    },
    note: 'Illustrative 150 MHz narrowband terrestrial link. Uses the narrowband rating, not the separate 20 W peak wideband specification.',
    referenceUrl: PRC117,
    referenceLabel: 'L3Harris AN/PRC-117G datasheet',
    values: { ...PORTABLE, frequencyMHz: 150, transmitDbm: 40 },
  },
  {
    id: 'prc148-mbitr',
    group: 'military',
    basis: 'published',
    label: 'Thales AN/PRC-148 JEM / MBITR · 5 W',
    propagation: 'terrain',
    specification: { band: '30–512 MHz', output: '0.1 / 0.5 / 1 / 3 / 5 W, waveform dependent' },
    note: 'Illustrative FM handheld link at 150 MHz. The published power choices depend on waveform; this example uses 5 W.',
    referenceUrl: PRC148,
    referenceLabel: 'Thales JEM / MBITR datasheet',
    values: { ...PORTABLE, frequencyMHz: 150, transmitDbm: 30 + 10 * Math.log10(5) },
  },
  {
    id: 'sincgars-rt1702',
    group: 'military',
    basis: 'published',
    label: 'SINCGARS RT-1702 · manpack 5 W',
    propagation: 'terrain',
    specification: {
      band: '30–88 MHz',
      output: '0.001 / 0.1 / 5 W; 50 W requires RF power amplifier',
    },
    note: 'Illustrative 60 MHz FM manpack link using the RT-1702 rating. This is not a generic rating for every SINCGARS model.',
    referenceUrl: SINCGARS,
    referenceLabel: 'L3Harris SINCGARS RT-1702 datasheet',
    values: {
      ...PORTABLE,
      frequencyMHz: 60,
      transmitDbm: 30 + 10 * Math.log10(5),
      transmitHeightM: 2,
      receiveHeightM: 2,
    },
  },
  {
    id: 'sincgars-rt1702-rfpa',
    group: 'military',
    basis: 'published',
    label: 'SINCGARS RT-1702 + RFPA · vehicle 50 W',
    propagation: 'terrain',
    specification: { band: '30–88 MHz', output: '50 W with the specified RF power amplifier' },
    note: 'Requires the external RF power amplifier. The selected 60 MHz and 3 m vehicle antenna are planning assumptions.',
    referenceUrl: SINCGARS,
    referenceLabel: 'L3Harris SINCGARS RT-1702 datasheet',
    values: {
      ...PORTABLE,
      frequencyMHz: 60,
      transmitDbm: 30 + 10 * Math.log10(50),
      transmitHeightM: 3,
      receiveHeightM: 2,
    },
  },
];
