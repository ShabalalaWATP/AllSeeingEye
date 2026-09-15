import type { BriefDraft } from '@/lib/api/researchBriefSchema';
import { missingPresetInputs, type PresetItem } from '@/lib/api/researchPresets';

const bundleStatus = {
  unverified_candidates: 'Candidate sources, unverified',
  declared_gaps: 'Declared coverage gap',
  unavailable: 'No available candidate',
};
const sourceStatus = {
  public_unverified: 'Public route, unverified',
  configured_unverified: 'Configured route, unverified',
  requirement_unknown: 'Setup unknown',
  requirement_missing: 'Setup missing',
  disabled: 'Disabled',
};

export function PresetReadiness({
  item,
  draft,
  applied,
}: {
  item: PresetItem;
  draft: BriefDraft;
  applied: boolean;
}) {
  const { preset, readiness } = item;
  const missing = applied ? missingPresetInputs(item, draft) : [];
  return (
    <div className="space-y-4 text-xs leading-5 text-muted">
      {preset.required_inputs.length > 0 && (
        <section aria-label="Required preset inputs">
          <h4 className="font-semibold text-text">Inputs to complete</h4>
          <ul className="mt-1 space-y-1">
            {preset.required_inputs.map((input) => (
              <li key={input.id}>
                <span className="font-medium text-text">{input.label}</span>
                {input.required ? ' · Required' : ' · Optional'}
                {applied && input.required
                  ? missing.includes(input.label)
                    ? ' · Still needed'
                    : ' · Provided'
                  : ''}
                <span className="block">{input.guidance}</span>
              </li>
            ))}
          </ul>
          {applied && missing.length > 0 && (
            <p className="mt-2 text-ember">Complete before running: {missing.join(', ')}.</p>
          )}
        </section>
      )}
      <section aria-label="Source readiness">
        <h4 className="font-semibold text-text">Source readiness</h4>
        <p>
          {readiness.candidate_provider_ids.length} candidate source
          {readiness.candidate_provider_ids.length === 1 ? '' : 's'} · {readiness.policy_version}
        </p>
        <ul className="mt-1 space-y-1">
          {readiness.source_bundles.map((bundle) => (
            <li key={bundle.id}>
              <span className="font-medium text-text">{bundle.id}</span>:{' '}
              {bundleStatus[bundle.status]}
              {bundle.gap_ids.length > 0 && ` (${bundle.gap_ids.join(', ')})`}
            </li>
          ))}
        </ul>
        {readiness.languages.some((row) => row.status === 'no_configured_route') && (
          <p className="mt-2 text-ember">
            No configured route for:{' '}
            {readiness.languages
              .filter((row) => row.status === 'no_configured_route')
              .map((row) => row.language)
              .join(', ')}
            . These language choices remain in the draft for review.
          </p>
        )}
        {readiness.gaps.length > 0 && (
          <ul className="mt-2 space-y-1" aria-label="Declared coverage gaps">
            {readiness.gaps.map((gap) => (
              <li key={gap.id}>
                <span className="font-medium text-text">{gap.name}</span>: {gap.reason}
              </li>
            ))}
          </ul>
        )}
        <details className="mt-2">
          <summary className="cursor-pointer text-text">
            Inspect {readiness.sources.length} source routes
          </summary>
          <ul className="mt-2 max-h-48 space-y-2 overflow-y-auto border-l border-line pl-3">
            {readiness.sources.map((source) => (
              <li key={source.id}>
                <span className="font-medium text-text">{source.name}</span> ·{' '}
                {sourceStatus[source.readiness]}
                {!source.scope_language_compatible && ' · Scope or language mismatch'}
                <span className="block">{source.constraints}</span>
              </li>
            ))}
          </ul>
        </details>
        <p className="mt-2">{readiness.note}</p>
      </section>
    </div>
  );
}
