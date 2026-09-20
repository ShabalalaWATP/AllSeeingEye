import type { calculateRf } from '@/lib/map/rfPlanning';
import { freeSpaceExplanation } from '@/lib/map/rfResultExplanation';
import { RfResultSummary } from './RfResultSummary';
import { RfEngineeringDetails } from './RfEngineeringDetails';

export function RfResults({ result }: { result: ReturnType<typeof calculateRf> }) {
  const radius = Math.min(result.horizonKm, result.sensitivityDistanceKm);
  return (
    <section
      aria-label="Free-space reference result"
      aria-live="polite"
      className="rf-budget-preview"
    >
      <RfResultSummary value={freeSpaceExplanation(result)} />
      <RfEngineeringDetails>
        <h3 className="rf-section-label">Ideal link budget · live preview</h3>
        <dl className="rf-budget-metrics">
          <div>
            <dt>Model distance limit</dt>
            <dd>
              {radius.toFixed(2)} km
              <small>
                Limited by{' '}
                {result.horizonKm <= result.sensitivityDistanceKm
                  ? 'radio horizon'
                  : 'sensitivity + reserve'}
              </small>
            </dd>
          </div>
          <div>
            <dt>Margin after reserve</dt>
            <dd className={result.planningMarginDb < 0 ? 'rf-budget-risk' : ''}>
              {result.planningMarginDb.toFixed(1)} dB
              <small>{result.reserveDb.toFixed(0)} dB planning reserve applied</small>
            </dd>
          </div>
        </dl>
        <p className="rf-help">
          The smaller of the smooth-Earth horizon and ideal distance at sensitivity plus reserve.
          The circle is a distance reference, not a coverage prediction or antenna beam.
        </p>
        <p className="rf-notice-warning">
          {result.beyondHorizon
            ? 'Beyond the model horizon. Free-space receive level is not a viable-link prediction.'
            : 'Inside the model horizon does not establish line of sight.'}
        </p>
        <p>Estimated receive level: {result.receivedDbm.toFixed(1)} dBm</p>
        <details className="rf-disclosure">
          <summary>Link budget and assumptions</summary>
          <div className="rf-disclosure-body">
            <div className="space-y-1 font-mono text-muted">
              <p>Free-space loss: {result.freeSpaceLossDb.toFixed(1)} dB</p>
              <p>Raw margin above sensitivity: {result.marginDb.toFixed(1)} dB</p>
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
              {result.reserveDb.toFixed(1)} dB planning reserve, unobstructed far-field propagation
              and aligned antenna gains. Heights use a smooth Earth with refraction factor k ={' '}
              {result.earthFactor.toFixed(3)}. No terrain, buildings, vegetation, weather,
              interference, diffraction or antenna pattern is modelled. Very short distances may
              fall outside the far-field assumption. HF skywave and satellite links are not
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
          </div>
        </details>
      </RfEngineeringDetails>
    </section>
  );
}
