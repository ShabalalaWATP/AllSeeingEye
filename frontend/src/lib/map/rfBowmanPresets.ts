import { DEFAULT_RF_INPUTS } from './rfPlanning';
import type { RfPreset } from './rfPresetTypes';
import { BOWMAN_REFERENCES } from './rfBowmanReferences';

const MANPACK = {
  ...DEFAULT_RF_INPUTS,
  transmitHeightM: 2,
  receiveHeightM: 2,
  transmitGainDbi: 0,
  receiveGainDbi: 0,
  sensitivityDbm: -110,
  distanceKm: 5,
};

/** Named planning roles, not inferred variant specifications or network configurations. */
export const RF_BOWMAN_PRESETS: readonly RfPreset[] = [
  {
    id: 'bowman-vhf-band',
    group: 'bowman',
    basis: 'illustrative',
    label: 'Bowman VHF manpack · 5 W scenario',
    propagation: 'terrain',
    note: 'Bowman-compatible antennas document a 30–88 MHz band. The selected 60 MHz and 5 W are planning assumptions, not verified PRC355/356 specifications.',
    referenceUrl: BOWMAN_REFERENCES[0].url,
    referenceLabel: BOWMAN_REFERENCES[0].title,
    values: { ...MANPACK, frequencyMHz: 60, transmitDbm: 30 + 10 * Math.log10(5) },
  },
  {
    id: 'bowman-vhf-vehicle',
    group: 'bowman',
    basis: 'illustrative',
    label: 'Bowman VHF vehicle · 50 W scenario',
    propagation: 'terrain',
    note: 'Vehicle-to-manpack example at 60 MHz, with a 3 m transmit antenna. The 50 W selection is an editable scenario, not a verified VRC357/358/359 power rating.',
    referenceUrl: BOWMAN_REFERENCES[0].url,
    referenceLabel: BOWMAN_REFERENCES[0].title,
    values: {
      ...MANPACK,
      frequencyMHz: 60,
      transmitDbm: 30 + 10 * Math.log10(50),
      transmitHeightM: 3,
    },
  },
  {
    id: 'bowman-prc325-groundwave',
    group: 'bowman',
    basis: 'illustrative',
    label: 'Bowman PRC325 HF · groundwave scenario',
    propagation: 'hf-groundwave',
    note: 'UK Parliament confirms the PRC325 HF manpack. Selected 7 MHz, 20 W and 3 m antennas are assumptions; that reference does not publish variant band or power specifications.',
    referenceUrl: BOWMAN_REFERENCES[1].url,
    referenceLabel: BOWMAN_REFERENCES[1].title,
    values: {
      ...MANPACK,
      frequencyMHz: 7,
      transmitDbm: 30 + 10 * Math.log10(20),
      transmitHeightM: 3,
      receiveHeightM: 3,
      distanceKm: 20,
    },
  },
  {
    id: 'bowman-prc325-nvis',
    group: 'bowman',
    basis: 'illustrative',
    label: 'Bowman PRC325 HF · NVIS scenario',
    propagation: 'hf-skywave',
    environment: { minElevationDeg: '60', maxElevationDeg: '90' },
    note: 'PRC325-labelled high-angle HF scenario at an assumed 5 MHz. Launch angles and ionospheric settings are editable; the skywave model does not calculate received power or a radio-specific antenna pattern.',
    referenceUrl: BOWMAN_REFERENCES[1].url,
    referenceLabel: BOWMAN_REFERENCES[1].title,
    values: {
      ...MANPACK,
      frequencyMHz: 5,
      transmitDbm: 30 + 10 * Math.log10(20),
      transmitHeightM: 5,
      receiveHeightM: 5,
      distanceKm: 100,
    },
  },
];
