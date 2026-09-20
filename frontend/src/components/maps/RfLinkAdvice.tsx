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
        <summary>Set practical antenna height limits</summary>
        <p className="rf-help">
          Enter the highest antenna you could realistically install above the ground. Blank applies
          no practical installation limit, so a calculated suggestion may be impractical.
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
          No antenna-height suggestion is available. The path may already pass the checks, terrain
          data may be missing, or changing one antenna alone may not be enough within your limits.
        </p>
      )}
      {advice && (
        <>
          <p className="font-medium">Possible improvement</p>
          {advice.kind === 'budget' ? (
            <p>
              The sampled terrain leaves enough clear space, but the signal estimate is short of
              your chosen allowance by {advice.shortfallDb.toFixed(1)} dB. Check the receiver
              setting against its specification, and review antenna gain and cable losses.
            </p>
          ) : (
            <>
              <p>
                Try comparing a {advice.site} antenna at{' '}
                <strong>{advice.heightM} m above ground</strong> (+{advice.addedM.toFixed(1)} m) in
                the calculator. This leaves enough clear space around the modelled signal path while
                the other antenna stays unchanged.
              </p>
              <p>
                Signal margin after your extra allowance: {advice.planningMarginDb.toFixed(1)} dB.{' '}
                {advice.status === 'clear'
                  ? 'This scenario passes the selected checks; it still needs testing on site.'
                  : 'The signal estimate would still fall short of your settings.'}
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
