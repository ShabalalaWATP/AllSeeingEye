import type { calculateRf } from '@/lib/map/rfPlanning';

export function RfResults({ result }: { result: ReturnType<typeof calculateRf> }) {
  const radius = Math.min(result.horizonKm, result.sensitivityDistanceKm);
  return (
    <div aria-live="polite" className="space-y-3 border-t border-line pt-3">
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded border border-cyan/30 bg-cyan/5 p-3">
          <p className="text-muted">Model distance limit</p>
          <p className="mt-1 font-mono text-lg text-cyan">{radius.toFixed(2)} km</p>
          <p className="mt-1 text-[10px] text-muted">
            Limited by{' '}
            {result.horizonKm <= result.sensitivityDistanceKm
              ? 'radio horizon'
              : 'receiver sensitivity'}
          </p>
        </div>
        <div className="rounded border border-line p-3">
          <p className="text-muted">Link margin</p>
          <p
            className={`mt-1 font-mono text-lg ${result.marginDb < 0 ? 'text-amber-300' : 'text-cyan'}`}
          >
            {result.marginDb.toFixed(1)} dB
          </p>
        </div>
      </div>
      <p className="text-muted">
        The smaller of the smooth-Earth horizon and ideal sensitivity distance. The circle is a
        distance reference, not a coverage prediction or antenna beam.
      </p>
      <p className="text-amber-300">
        {result.beyondHorizon
          ? 'Beyond the model horizon. Free-space receive level is not a viable-link prediction.'
          : 'Inside the model horizon does not establish line of sight.'}
      </p>
      <p>Estimated receive level: {result.receivedDbm.toFixed(1)} dBm</p>
      <details className="rounded border border-line p-3">
        <summary className="cursor-pointer text-text">Link budget and assumptions</summary>
        <div className="mt-3 space-y-1 font-mono text-muted">
          <p>Free-space loss: {result.freeSpaceLossDb.toFixed(1)} dB</p>
          <p>
            Ideal sensitivity distance:{' '}
            {Number(result.sensitivityDistanceKm.toPrecision(3)).toLocaleString('en-GB', {
              maximumSignificantDigits: 3,
            })}{' '}
            km
          </p>
          <p>Model radio horizon: {result.horizonKm.toFixed(1)} km</p>
          <p>Midpoint first Fresnel radius: {result.midpointFresnelM.toFixed(1)} m</p>
        </div>
        <p className="mt-3 text-muted">
          Zero fade margin, unobstructed far-field propagation and aligned antenna gains. Heights
          use a smooth Earth with standard 4/3 refraction. No terrain, buildings, vegetation,
          weather, interference, diffraction or antenna pattern is modelled. Very short distances
          may fall outside the far-field assumption. HF skywave and satellite links are not
          supported.
        </p>
        <p className="mt-2 text-muted">
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
      </details>
    </div>
  );
}
