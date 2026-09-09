import { useState } from 'react';
import { calculateRf, DEFAULT_RF_INPUTS, RF_FIELDS } from '@/lib/map/rfPlanning';
import type { RfInputs } from '@/lib/map/rfPlanning';

export function RfCalculatorPanel({
  measuredDistanceKm,
}: {
  measuredDistanceKm?: number | undefined;
}) {
  const [values, setValues] = useState<Record<keyof RfInputs, string>>(
    () =>
      Object.fromEntries(
        Object.entries(DEFAULT_RF_INPUTS).map(([key, value]) => [key, String(value)]),
      ) as Record<keyof RfInputs, string>,
  );
  let result: ReturnType<typeof calculateRf> | null = null;
  let error: string | null = null;
  try {
    result = calculateRf(
      Object.fromEntries(
        Object.entries(values).map(([key, value]) => [key, value.trim() ? Number(value) : NaN]),
      ) as unknown as RfInputs,
    );
  } catch (caught) {
    error = caught instanceof Error ? caught.message : 'Check the inputs.';
  }
  return (
    <section aria-label="RF planning calculator" className="space-y-3 text-xs">
      <h2 className="font-mono uppercase tracking-widest text-cyan">RF link estimate</h2>
      <p className="text-muted">
        Free-space planning for a single terrestrial link. Calculations stay in this browser.
      </p>
      {measuredDistanceKm !== undefined &&
        Number.isFinite(measuredDistanceKm) &&
        measuredDistanceKm > 0 && (
          <button
            type="button"
            className="min-h-9 rounded border border-line px-2 text-cyan"
            onClick={() =>
              setValues((previous) => ({ ...previous, distanceKm: measuredDistanceKm.toFixed(3) }))
            }
          >
            Use measured path ({measuredDistanceKm.toFixed(3)} km)
          </button>
        )}
      <div className="grid grid-cols-2 gap-2">
        {RF_FIELDS.map(({ key, label, min, max }) => (
          <label key={key} className="block text-muted">
            {label}
            <input
              type="number"
              min={min}
              max={max}
              step="any"
              value={values[key]}
              onChange={(event) =>
                setValues((previous) => ({ ...previous, [key]: event.target.value }))
              }
              className="mt-1 w-full rounded border border-line bg-ground p-2 text-text"
            />
          </label>
        ))}
      </div>
      {error && (
        <p role="alert" className="text-amber-300">
          {error}
        </p>
      )}
      {result && (
        <div aria-live="polite" className="space-y-1 border-t border-line pt-2 font-mono">
          <p>Free-space loss: {result.freeSpaceLossDb.toFixed(1)} dB</p>
          <p>Estimated receive level: {result.receivedDbm.toFixed(1)} dBm</p>
          <p>Margin above sensitivity: {result.marginDb.toFixed(1)} dB</p>
          <p>
            Ideal sensitivity distance:{' '}
            {Number(result.sensitivityDistanceKm.toPrecision(3)).toLocaleString('en-GB', {
              maximumSignificantDigits: 3,
            })}{' '}
            km
          </p>
          <p>Model radio horizon: {result.horizonKm.toFixed(1)} km</p>
          <p>Midpoint first Fresnel radius: {result.midpointFresnelM.toFixed(1)} m</p>
          <p className="font-sans text-amber-300">
            {result.beyondHorizon
              ? 'Beyond the model horizon. Free-space receive level is not a viable-link prediction.'
              : 'Inside the model horizon does not establish line of sight.'}
          </p>
        </div>
      )}
      <p className="text-muted">
        Sensitivity distance is an idealised free-space upper estimate at zero link margin, not the
        actual signal range. Compare it with the radio horizon separately; neither establishes a
        usable link. Very short estimates may fall outside the far-field assumption.
      </p>
      <p className="text-muted">
        Assumes unobstructed far-field propagation and aligned antenna gains. Heights use a smooth
        Earth with standard 4/3 refraction. No terrain, buildings, vegetation, weather,
        interference, diffraction or fade margin is modelled. A positive margin does not confirm
        usable coverage or Fresnel clearance.
      </p>
      <p className="text-muted">
        <a
          href="https://www.itu.int/rec/R-REC-P.525/en"
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          ITU-R P.525
        </a>{' '}
        ·{' '}
        <a
          href="https://www.oc.nps.edu/NWDC_EM_Course/course_materials/module3_1.html"
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          Radio-horizon assumptions
        </a>
      </p>
    </section>
  );
}
