import { Alert } from '@/components/ui/Alert';
import type { ResearchPreflight } from '@/lib/api/researchPreflight';

const tierName = { quick: 'Basic', detailed: 'Deep', advanced: 'Advanced' };
const humanise = (value: string) => value.replaceAll('_', ' ');
const utc = (value: string) =>
  `${new Date(value).toISOString().slice(0, 16).replace('T', ' ')} UTC`;

export function BriefPreflightResult({ preview }: { preview: ResearchPreflight }) {
  const required = preview.requirements.filter((row) => row.required);
  const excess = required.length - preview.budget.required_question_ceiling;
  const excluded = preview.sources.filter((row) => !row.candidate_unverified);
  return (
    <section
      aria-label="Saved brief preflight"
      className="space-y-4 border-l-2 border-ember pl-4 text-sm"
    >
      <header>
        <h3 className="font-semibold text-text">Preflight: revision {preview.revision}</h3>
        <p className="text-xs text-muted">
          {preview.title} · Checked {utc(preview.as_of)}
        </p>
      </header>
      <Alert tone="warning">
        Preview only. No provider or model calls were made. Source connectivity, exact coverage,
        authorisation at run time and model capacity have not been checked.
      </Alert>
      <section aria-label="Preflight question and period" className="space-y-1">
        <h4 className="font-semibold">Question and period</h4>
        <p>{preview.question}</p>
        <p className="text-muted">
          {utc(preview.since)} to {utc(preview.until)} · {humanise(preview.time_basis)} basis
          {preview.forecast_horizon_days !== null &&
            ` · ${preview.forecast_horizon_days}-day forecast horizon`}
        </p>
        <p className="text-xs text-muted">
          {preview.scope.country_isos.length > 0
            ? preview.scope.country_isos.join(', ')
            : 'No country filter'}
          {' · '}
          {humanise(preview.scope.focus)}
          {preview.scope.subject && ` · ${preview.scope.subject}`}
          {preview.scope.area_sha256 && ` · Area SHA-256 ${preview.scope.area_sha256}`}
        </p>
        {preview.scope.saved_map_resolution_required && (
          <p className="text-xs text-ember">
            Saved-map geometry must be resolved again at run admission.
          </p>
        )}
      </section>
      <section aria-label="Preflight requirements and limits" className="space-y-1">
        <h4 className="font-semibold">Requirements and limits</h4>
        <p>
          {required.length} required of {preview.requirements.length} selected ·{' '}
          {tierName[preview.budget.tier]} allows up to {preview.budget.required_question_ceiling}{' '}
          required questions.
        </p>
        {excess > 0 && (
          <Alert tone="warning">
            Reduce {excess} required question{excess === 1 ? '' : 's'} in an editable brief before
            running. No questions are dropped automatically.
          </Alert>
        )}
        <p className="text-xs text-muted">
          To use a lower depth, edit the requirements and save a new revision. Preview never removes
          questions automatically.
        </p>
        <ol className="list-inside list-decimal space-y-1 text-xs text-muted">
          {preview.requirements.map((row) => (
            <li key={row.id}>
              <span className="font-mono text-text">{row.id}</span> · {row.question} (
              {row.required ? 'required' : 'optional'}, priority {row.priority})
            </li>
          ))}
        </ol>
        <p className="text-xs text-muted">
          Collection ceiling: {preview.budget.source_operation_ceiling} source operations,{' '}
          {preview.budget.collection_second_ceiling} seconds. Model ceiling:{' '}
          {preview.budget.model_call_ceiling} calls and{' '}
          {preview.budget.output_token_ceiling.toLocaleString('en-GB')} output tokens. No capacity
          was reserved.
        </p>
      </section>
      <section aria-label="Preflight source coverage" className="space-y-1">
        <h4 className="font-semibold">Source readiness</h4>
        <p>
          {preview.candidate_provider_ids.length} unverified candidate
          {preview.candidate_provider_ids.length === 1 ? '' : 's'} · {excluded.length} excluded ·{' '}
          {humanise(preview.source_policy)} selection.
        </p>
        {preview.gaps.length > 0 && (
          <ul className="list-inside list-disc text-xs text-muted" aria-label="Preflight gaps">
            {preview.gaps.map((gap) => (
              <li key={gap.id}>
                <strong>{gap.name}:</strong> {gap.reason}
              </li>
            ))}
          </ul>
        )}
        {preview.unknown_source_ids.length > 0 && (
          <p className="text-xs text-ember">
            Unknown selected source IDs: {preview.unknown_source_ids.join(', ')}.
          </p>
        )}
        {preview.review_reasons.length > 0 && (
          <ul
            className="list-inside list-disc text-xs text-ember"
            aria-label="Preflight review reasons"
          >
            {preview.review_reasons.map((reason) => (
              <li key={reason}>{humanise(reason)}</li>
            ))}
          </ul>
        )}
        <details>
          <summary className="cursor-pointer text-xs text-text">
            Inspect {preview.sources.length} source routes and exclusions
          </summary>
          <ul className="mt-2 max-h-56 space-y-2 overflow-y-auto border-l border-line pl-3 text-xs text-muted">
            {preview.sources.map((row) => (
              <li key={row.capability.id}>
                <span className="font-medium text-text">{row.capability.name}</span>
                {' · '}
                {row.candidate_unverified
                  ? 'Candidate, unverified'
                  : `Excluded: ${row.exclusion_reasons.map(humanise).join(', ')}`}
                {' · '}
                {humanise(row.readiness)}
                <span className="block">
                  {row.capability.support.constraints} {row.date_note}
                </span>
              </li>
            ))}
          </ul>
        </details>
      </section>
      <p className="text-xs text-muted">{preview.duration_note}</p>
      <p className="text-xs text-muted">{preview.coverage_note}</p>
    </section>
  );
}
