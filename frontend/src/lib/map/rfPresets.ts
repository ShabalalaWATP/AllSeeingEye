import { DEFAULT_RF_INPUTS } from './rfPlanning';
import type { RfInputs } from './rfPlanning';
import type { RfEnvironment } from './rfDraft';

export interface RfPreset {
  id: string;
  label: string;
  note: string;
  values: RfInputs;
  referenceUrl?: string;
  referenceLabel?: string;
  propagation?: 'terrain' | 'hf-groundwave' | 'hf-skywave';
  environment?: Partial<RfEnvironment>;
}

/** Public evidence only. Frequencies below are illustrative choices, not network settings. */
export const BOWMAN_REFERENCES = [
  {
    title: 'Cooper Antennas: Bowman VHF band',
    url: 'https://www.cooperantennas.com/airborne-antennas.php',
    detail:
      'Manufacturer lists Bowman-compatible antennas covering 30–88 MHz. This documents a supported band, not radio output power or operational frequencies.',
  },
  {
    title: 'UK Parliament: PRC325 HF manpack',
    url: 'https://hansard.parliament.uk/Commons/2005-03-02/debates/a9d8af13-2718-4f0c-86c0-bbf5e3f9f31f/BowmanSystem',
    detail:
      'Ministerial answer identifies the Bowman PRC325 HF manpack. It does not publish power settings or a variant datasheet.',
  },
  {
    title: 'General Dynamics: Bowman radio families',
    url: 'https://gdmissionsystems.com/articles/2015/09/15/news-release-general-dynamics-shows-its-strength-at-dsei-2015',
    detail:
      'Manufacturer describes a Bowman installation supporting HF, VHF and UHF voice and data. No verified variant power table is provided.',
  },
] as const;

/** Illustrative planning inputs, not equipment specifications or regulatory limits. */
export const RF_PRESETS: readonly RfPreset[] = [
  {
    id: 'custom',
    label: 'Custom radio link',
    note: 'Set the values from your equipment specifications.',
    values: DEFAULT_RF_INPUTS,
  },
  {
    id: 'hf-portable',
    propagation: 'hf-groundwave',
    label: 'HF portable SSB · 7 MHz',
    note: 'Illustrative 20 W HF link. Choose groundwave or skywave and enter environmental assumptions. Heights, antenna gains and sensitivity are examples.',
    values: {
      ...DEFAULT_RF_INPUTS,
      frequencyMHz: 7,
      transmitDbm: 10 * Math.log10(20000),
      transmitHeightM: 3,
      receiveHeightM: 3,
      transmitGainDbi: 0,
      receiveGainDbi: 0,
      sensitivityDbm: -110,
      distanceKm: 20,
    },
  },
  {
    id: 'hf-nvis',
    propagation: 'hf-skywave',
    environment: { minElevationDeg: '60', maxElevationDeg: '90' },
    label: 'HF high-angle / NVIS scenario · 5 MHz',
    note: 'Illustrative 20 W high-angle skywave scenario. Set high launch angles and ionospheric conditions in skywave mode. Antenna height alone does not define its launch pattern.',
    values: {
      ...DEFAULT_RF_INPUTS,
      frequencyMHz: 5,
      transmitDbm: 10 * Math.log10(20000),
      transmitHeightM: 5,
      receiveHeightM: 5,
      transmitGainDbi: 0,
      receiveGainDbi: 0,
      sensitivityDbm: -110,
      distanceKm: 100,
    },
  },
  {
    id: 'falcon-ii-hf',
    propagation: 'hf-groundwave',
    label: 'Harris RF-5800H-MP · HF 20 W',
    note: 'Manufacturer DS-211H documents a 1.6–59.999 MHz base radio with 1/5/20 W PEP settings. Selected 7 MHz, heights, gains and sensitivity are planning assumptions. This is not a verified Bowman variant configuration.',
    referenceUrl: 'https://w2hx.com/x/Harris/RF-5800/Docs/5800H_MP.pdf',
    referenceLabel: 'Harris DS-211H manufacturer datasheet (2004, archived copy)',
    values: {
      ...DEFAULT_RF_INPUTS,
      frequencyMHz: 7,
      transmitDbm: 10 * Math.log10(20000),
      transmitHeightM: 3,
      receiveHeightM: 3,
      transmitGainDbi: 0,
      receiveGainDbi: 0,
      sensitivityDbm: -110,
      distanceKm: 20,
    },
  },
  {
    id: 'bowman-vhf-band',
    propagation: 'terrain',
    label: 'Bowman VHF band reference · 60 MHz',
    note: 'The manufacturer documents a 30–88 MHz Bowman-compatible antenna band. Selected 60 MHz, 5 W power, heights, gains and receiver sensitivity are editable illustrative assumptions, not verified PRC355/356 settings or an operational network configuration.',
    referenceUrl: BOWMAN_REFERENCES[0].url,
    referenceLabel: BOWMAN_REFERENCES[0].title,
    values: {
      ...DEFAULT_RF_INPUTS,
      frequencyMHz: 60,
      transmitDbm: 10 * Math.log10(5000),
      transmitHeightM: 2,
      receiveHeightM: 2,
      transmitGainDbi: 0,
      receiveGainDbi: 0,
      sensitivityDbm: -110,
      distanceKm: 5,
    },
  },
  {
    id: 'handheld',
    label: 'UHF handheld · 446 MHz',
    note: 'Example short-range handhelds, 0.5 W and 1.5 m antennas.',
    values: {
      ...DEFAULT_RF_INPUTS,
      frequencyMHz: 446,
      transmitDbm: 27,
      transmitHeightM: 1.5,
      receiveHeightM: 1.5,
      distanceKm: 2,
      transmitGainDbi: 0,
      receiveGainDbi: 0,
      sensitivityDbm: -110,
    },
  },
  {
    id: 'vhf',
    label: 'VHF mobile / base · 150 MHz',
    note: 'Example 25 W mobile-to-base link. Heights are above local ground.',
    values: {
      ...DEFAULT_RF_INPUTS,
      frequencyMHz: 150,
      transmitDbm: 44,
      transmitHeightM: 15,
      receiveHeightM: 2,
      sensitivityDbm: -115,
    },
  },
  {
    id: 'marine',
    label: 'Marine VHF · 156 MHz',
    note: 'Example 25 W ship radios with antennas 10 m and 5 m above sea level.',
    values: {
      ...DEFAULT_RF_INPUTS,
      frequencyMHz: 156,
      transmitDbm: 44,
      transmitHeightM: 10,
      receiveHeightM: 5,
      sensitivityDbm: -115,
    },
  },
  {
    id: 'airband',
    label: 'Airband VHF · 125 MHz',
    note: 'Example 10 W ground-to-air link, aircraft 1,000 m above the reference surface.',
    values: {
      ...DEFAULT_RF_INPUTS,
      frequencyMHz: 125,
      transmitDbm: 40,
      transmitHeightM: 10,
      receiveHeightM: 1000,
      distanceKm: 50,
      sensitivityDbm: -107,
    },
  },
  {
    id: 'uhf',
    label: 'UHF repeater · 450 MHz',
    note: 'Example 25 W base station with a 30 m antenna and a handheld receiver.',
    values: {
      ...DEFAULT_RF_INPUTS,
      frequencyMHz: 450,
      transmitDbm: 44,
      transmitHeightM: 30,
      receiveHeightM: 1.5,
      transmitGainDbi: 5,
      receiveGainDbi: 0,
      sensitivityDbm: -115,
    },
  },
  {
    id: 'telemetry',
    label: 'Telemetry / LoRa · 868 MHz',
    note: 'Example low-power telemetry. Actual sensitivity depends strongly on bandwidth and data rate.',
    values: {
      ...DEFAULT_RF_INPUTS,
      frequencyMHz: 868,
      transmitDbm: 14,
      transmitHeightM: 5,
      receiveHeightM: 2,
      sensitivityDbm: -130,
      distanceKm: 5,
    },
  },
  {
    id: 'wifi24',
    label: 'Wi-Fi · 2.4 GHz',
    note: 'Example 100 m outdoor link. Receiver sensitivity is data-rate dependent.',
    values: {
      ...DEFAULT_RF_INPUTS,
      frequencyMHz: 2400,
      transmitDbm: 20,
      transmitHeightM: 3,
      receiveHeightM: 2,
      sensitivityDbm: -85,
      distanceKm: 0.1,
    },
  },
  {
    id: 'wifi5',
    label: 'Directional Wi-Fi · 5.8 GHz',
    note: 'Example aligned directional antennas. A circle is only a distance reference, not the antenna beam.',
    values: {
      ...DEFAULT_RF_INPUTS,
      frequencyMHz: 5800,
      transmitDbm: 20,
      transmitHeightM: 10,
      receiveHeightM: 10,
      transmitGainDbi: 18,
      receiveGainDbi: 18,
      sensitivityDbm: -85,
      distanceKm: 2,
    },
  },
  {
    id: 'microwave',
    label: 'Microwave point-to-point · 6 GHz',
    note: 'Example directional link. Choose terrain mode to screen sampled obstructions. Rain fading and antenna patterns are not modelled.',
    values: {
      ...DEFAULT_RF_INPUTS,
      frequencyMHz: 6000,
      transmitDbm: 20,
      transmitHeightM: 30,
      receiveHeightM: 30,
      transmitGainDbi: 24,
      receiveGainDbi: 24,
      sensitivityDbm: -80,
      distanceKm: 10,
    },
  },
];
