import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { rfLinkAdvice } from '@/lib/map/rfLinkAdvice';

export function RfLinkAdvice({ analysis }: { analysis: Extract<RfAnalysis, { kind: 'terrain' }> }) {
  const advice = rfLinkAdvice(analysis);
  if (!advice) return null;
  return (
    <section
      aria-label="Automatic link improvement check"
      className="rf-result-next-step space-y-2"
    >
      <p className="font-medium">Possible improvement</p>
      {advice.kind === 'budget' ? (
        <p>
          Terrain clearance passes, but the model needs another {advice.shortfallDb.toFixed(1)} dB
          of usable margin. Check receiver sensitivity for your operating mode, antenna gain and
          cable losses.
        </p>
      ) : (
        <>
          <p>
            In a calculated scenario, raising the {advice.site} antenna to{' '}
            <strong>{advice.heightM} m above ground</strong> (+{advice.addedM.toFixed(1)} m) clears
            the sampled Fresnel screen while the other site stays unchanged.
          </p>
          <p>
            Remaining margin after your reserve: {advice.planningMarginDb.toFixed(1)} dB.{' '}
            {advice.status === 'clear'
              ? 'This scenario passes the sampled checks.'
              : 'The link would still fall short on signal margin.'}
          </p>
          <p>
            This uses the same coarse terrain data. Check whether that mast height is practical and
            verify site clearance before changing your setup.
          </p>
        </>
      )}
    </section>
  );
}
