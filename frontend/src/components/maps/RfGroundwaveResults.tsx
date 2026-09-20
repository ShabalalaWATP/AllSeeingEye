import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { analysisExplanation } from '@/lib/map/rfResultExplanation';
import { RfEngineeringDetails } from './RfEngineeringDetails';
import { RfGroundwaveEngineering } from './RfGroundwaveEngineering';
import { RfResultSummary } from './RfResultSummary';

export function RfGroundwaveResults({
  analysis,
}: {
  analysis: Extract<RfAnalysis, { kind: 'hf-groundwave' }>;
}) {
  return (
    <section aria-label="HF groundwave model results" className="space-y-3">
      <RfResultSummary value={analysisExplanation(analysis)} />
      <RfEngineeringDetails>
        <RfGroundwaveEngineering analysis={analysis} />
      </RfEngineeringDetails>
    </section>
  );
}
