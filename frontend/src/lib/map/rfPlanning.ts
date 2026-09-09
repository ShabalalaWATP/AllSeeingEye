/** Free-space link budget, ITU-R P.525. No terrain or interference model. */
export interface RfInputs {
  distanceKm: number;
  frequencyMHz: number;
  transmitDbm: number;
  transmitGainDbi: number;
  receiveGainDbi: number;
  lossesDb: number;
  sensitivityDbm: number;
  transmitHeightM: number;
  receiveHeightM: number;
}

export const RF_FIELDS: readonly {
  key: keyof RfInputs;
  label: string;
  min: number;
  max: number;
}[] = [
  { key: 'distanceKm', label: 'Path length (km)', min: 0.001, max: 2000 },
  { key: 'frequencyMHz', label: 'Frequency (MHz)', min: 30, max: 100000 },
  { key: 'transmitDbm', label: 'Transmit power (dBm)', min: -100, max: 100 },
  { key: 'transmitGainDbi', label: 'Transmit gain (dBi)', min: -30, max: 80 },
  { key: 'receiveGainDbi', label: 'Receive gain (dBi)', min: -30, max: 80 },
  { key: 'lossesDb', label: 'Combined cable / other losses (dB)', min: 0, max: 100 },
  { key: 'sensitivityDbm', label: 'Receiver sensitivity (dBm)', min: -200, max: 0 },
  { key: 'transmitHeightM', label: 'Transmit height above ground (m)', min: 0, max: 10000 },
  { key: 'receiveHeightM', label: 'Receive height above ground (m)', min: 0, max: 10000 },
];

export const DEFAULT_RF_INPUTS: RfInputs = {
  distanceKm: 10,
  frequencyMHz: 900,
  transmitDbm: 30,
  transmitGainDbi: 2,
  receiveGainDbi: 2,
  lossesDb: 2,
  sensitivityDbm: -100,
  transmitHeightM: 10,
  receiveHeightM: 2,
};

export function calculateRf(input: RfInputs) {
  for (const { key, label, min, max } of RF_FIELDS) {
    if (!Number.isFinite(input[key]) || input[key] < min || input[key] > max)
      throw new Error(`${label}: enter a value from ${min} to ${max}.`);
  }
  const wavelengthM = 299792458 / (input.frequencyMHz * 1e6);
  const freeSpaceLossDb = 20 * Math.log10((4 * Math.PI * input.distanceKm * 1000) / wavelengthM);
  const receivedDbm =
    input.transmitDbm +
    input.transmitGainDbi +
    input.receiveGainDbi -
    input.lossesDb -
    freeSpaceLossDb;
  // Invert the same free-space equation at zero margin above sensitivity.
  // Work in logarithms so intermediate powers cannot overflow before scaling.
  const allowableLossDb =
    input.transmitDbm +
    input.transmitGainDbi +
    input.receiveGainDbi -
    input.lossesDb -
    input.sensitivityDbm;
  const logDistanceKm = allowableLossDb / 20 + Math.log10(wavelengthM / (4 * Math.PI * 1000));
  const sensitivityDistanceKm = 10 ** logDistanceKm;
  if (!Number.isFinite(sensitivityDistanceKm) || sensitivityDistanceKm <= 0)
    throw new Error('The sensitivity distance is outside the numerical calculation range.');
  // Approximate smooth-Earth horizons with standard refraction (k = 4/3).
  const horizon = (height: number) => Math.sqrt(2 * (4 / 3) * 6371000 * height) / 1000;
  const horizonKm = horizon(input.transmitHeightM) + horizon(input.receiveHeightM);
  return {
    freeSpaceLossDb,
    receivedDbm,
    marginDb: receivedDbm - input.sensitivityDbm,
    sensitivityDistanceKm,
    horizonKm,
    beyondHorizon: input.distanceKm > horizonKm,
    midpointFresnelM: Math.sqrt((wavelengthM * input.distanceKm * 1000) / 4),
  };
}
