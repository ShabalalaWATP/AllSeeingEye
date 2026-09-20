import { useState } from 'react';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { rfLinkAdvice } from '@/lib/map/rfLinkAdvice';

export function RfLinkAdvice({ analysis }: { analysis: Extract<RfAnalysis, { kind: 'terrain' }> }) {
  const [limits, setLimits] = useState({ transmitter: '', receiver: '' });
  const valid = Object.values(limits).every(
    (value) =>
      value === '' ||
      (Number.isFinite(Number(value)) && Number(value) >= 0 && Number(value) <= 10000),
  );
  const advice = valid
    ? rfLinkAdvice(
        analysis,
        Object.fromEntries(
          Object.entries(limits)
            .filter(([, value]) => value !== '')
            .map(([key, value]) => [key, Number(value)]),
        ),
      )
    : null;
  if (!analysis.terrain.path && !advice) return null;
  return (
    <section
      aria-label="Automatic link improvement check"
      className="rf-result-next-step space-y-2"
    >
      <details>
        <summary>Feasible mast heights</summary>
        <p className="rf-help">
          Limit suggested heights above ground. Blank leaves the model's 10,000 m numerical ceiling;
          this is not a recommended mast height.
        </p>
        {(['transmitter', 'receiver'] as const).map((site) => (
          <label className="rf-field" key={site}>
            <span>Maximum {site} mast (m)</span>
            <input
              type="number"
              min={0}
              max={10000}
              value={limits[site]}
              onChange={(event) =>
                setLimits((previous) => ({ ...previous, [site]: event.target.value }))
              }
            />
          </label>
        ))}
      </details>
      {!valid && <p role="alert">Enter a maximum height from 0 to 10,000 m.</p>}
      {valid && !advice && (
        <p className="rf-help">
          No single-site improvement suggestion within these limits. Missing terrain or sufficient
          clearance may also leave no suggestion.
        </p>
      )}
      {advice && (
        <>
          <p className="font-medium">Possible improvement</p>
          {advice.kind === 'budget' ? (
            <p>
              Terrain clearance passes, but the model needs another {advice.shortfallDb.toFixed(1)}{' '}
              dB of usable margin. Check receiver sensitivity for your operating mode, antenna gain
              and cable losses.
            </p>
          ) : (
            <>
              <p>
                In a calculated scenario, raising the {advice.site} antenna to{' '}
                <strong>{advice.heightM} m above ground</strong> (+{advice.addedM.toFixed(1)} m)
                clears the sampled Fresnel screen while the other site stays unchanged.
              </p>
              <p>
                Remaining margin after your reserve: {advice.planningMarginDb.toFixed(1)} dB.{' '}
                {advice.status === 'clear'
                  ? 'This scenario passes the sampled checks.'
                  : 'The link would still fall short on signal margin.'}
              </p>
              <p>
                This uses the same coarse terrain data. Check whether that mast height is practical
                and verify site clearance before changing your setup.
              </p>
            </>
          )}
        </>
      )}
    </section>
  );
}
