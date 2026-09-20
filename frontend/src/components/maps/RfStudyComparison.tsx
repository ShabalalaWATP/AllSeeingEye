import type { RfDraft } from '@/lib/map/rfDraft';
import { studyInputDifferences, type RfStudySnapshot } from '@/lib/map/rfStudy';
export function RfStudyComparison({
  baseline,
  draft,
  current,
  onClear,
}: {
  baseline: RfStudySnapshot;
  draft: RfDraft;
  current: () => RfStudySnapshot;
  onClear: () => void;
}) {
  let candidate: RfStudySnapshot | null = null;
  try {
    candidate = current();
  } catch {
    /* Incomplete edits have no comparable result. */
  }
  const differences = studyInputDifferences(baseline, draft);
  if (
    candidate &&
    JSON.stringify([baseline.origin, baseline.receiver]) !==
      JSON.stringify([candidate.origin, candidate.receiver])
  )
    differences.push('Site coordinates');
  for (const [key, label] of [
    ['environment', 'Environment'],
    ['engineering', 'Planning assumptions'],
    ['antenna', 'Antenna pattern'],
    ['propagation', 'Propagation model'],
    ['study', 'Study type'],
    ['automaticHfMode', 'Automatic HF scenario'],
    ['radiusMode', 'Radius mode'],
  ] as const)
    if (JSON.stringify(baseline.draft[key]) !== JSON.stringify(draft[key])) differences.push(label);
  const comparable = baseline.result?.kind === candidate?.result?.kind;
  const margin =
    comparable && baseline.result?.marginDb != null && candidate?.result?.marginDb != null
      ? candidate.result.marginDb - baseline.result.marginDb
      : null;
  return (
    <section aria-label="Radio comparison baseline" className="space-y-2">
      <p>
        Baseline: {new Date(baseline.savedAt).toLocaleString()} · {baseline.provenance.model}
      </p>
      <p>
        Frozen result: {baseline.result?.status ?? 'No analysis saved'}
        {baseline.result?.marginDb != null
          ? ` · ${baseline.result.marginDb.toFixed(1)} dB planning margin`
          : ''}
      </p>
      <p>Changed inputs: {differences.join(', ') || 'None'}.</p>
      {margin !== null ? (
        <p>
          Current planning margin: {candidate?.result?.marginDb?.toFixed(1)} dB (
          {margin >= 0 ? '+' : ''}
          {margin.toFixed(1)} dB against baseline).
        </p>
      ) : (
        <p>
          Run a matching model to compare available result margins. Groundwave curves and
          geometry-only scenarios do not have a single saved link margin.
        </p>
      )}
      {baseline.terrainEvidence && (
        <p>
          Baseline includes {baseline.terrainEvidence.samples.length} terrain samples at source zoom{' '}
          {baseline.terrainEvidence.zoom}. The export retains these samples; reopening uses a fresh
          analysis.
        </p>
      )}
      <button type="button" className="rf-text-button" onClick={onClear}>
        Clear baseline
      </button>
    </section>
  );
}
