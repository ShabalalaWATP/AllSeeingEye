import type { Ref } from 'react';

import type { BriefDraft } from '@/lib/api/researchBriefSchema';

export const BRIEF_STEPS = [
  {
    id: 'brief',
    label: 'Brief',
    title: 'Define your brief',
    hint: 'Start with a question or a saved starter.',
  },
  {
    id: 'scope',
    label: 'Scope',
    title: 'Scope and perspective',
    hint: 'Separate the evidence period from any forward-looking outlook.',
  },
  {
    id: 'depth',
    label: 'Depth',
    title: 'Depth and coverage',
    hint: 'Choose the depth, then review source readiness and limits.',
  },
  {
    id: 'run',
    label: 'Run',
    title: 'Review and run',
    hint: 'Save, run once or subscribe using the same brief.',
  },
] as const;
export type BriefStep = (typeof BRIEF_STEPS)[number]['id'];

export function BriefJourney({
  step,
  change,
  busy,
  headingRef,
}: {
  step: BriefStep;
  change: (step: BriefStep) => void;
  busy: boolean;
  headingRef: Ref<HTMLHeadingElement>;
}) {
  const selected = BRIEF_STEPS.find((entry) => entry.id === step) ?? BRIEF_STEPS[0];
  return (
    <>
      <nav aria-label="Research stages">
        <ol className="grid min-w-0 grid-cols-4 gap-1 border-b border-line">
          {BRIEF_STEPS.map((entry, index) => (
            <li key={entry.id} className="min-w-0">
              <button
                type="button"
                aria-label={`${index + 1} ${entry.label}`}
                disabled={busy}
                onClick={() => change(entry.id)}
                aria-current={entry.id === step ? 'step' : undefined}
                aria-controls={`brief-stage-${entry.id}`}
                className={`flex min-h-12 w-full flex-wrap items-center justify-center gap-1 border-b-2 px-1 py-3 text-xs transition-colors motion-reduce:transition-none sm:gap-2 sm:text-sm ${entry.id === step ? 'border-ember text-text' : 'border-transparent text-muted hover:text-text'} disabled:opacity-50`}
              >
                <span className="font-mono text-ember">{index + 1}</span>
                {entry.label}
              </button>
            </li>
          ))}
        </ol>
      </nav>
      <div>
        <h3 ref={headingRef} tabIndex={-1} className="text-lg font-semibold outline-offset-4">
          {selected.title}
        </h3>
        <p className="mt-1 text-sm text-muted">{selected.hint}</p>
      </div>
    </>
  );
}

export function briefIssueStep(message: string): BriefStep {
  if (
    /observation|scope\.|lens\.|collection.languages|output.language|UTC|Recorded history/.test(
      message,
    )
  )
    return 'scope';
  if (/depth|limits\.|monitoring\.|collection\.|output\.|private_inputs/.test(message))
    return 'depth';
  return 'brief';
}

export function BriefRunSummary({ draft }: { draft: BriefDraft }) {
  const { observation, scope } = draft;
  const period =
    observation.policy === 'explicit'
      ? `${observation.since ?? 'Start needed'} to ${observation.until ?? 'End needed'}`
      : observation.policy === 'relative'
        ? `Last ${observation.lookback_hours ?? '…'} hours, resolved when the run starts`
        : 'Product default, resolved when the run starts';
  return (
    <section aria-label="Brief run summary" className="space-y-4 text-sm">
      <p className="break-words text-lg leading-relaxed">
        {draft.question.main || 'Add your research question.'}
      </p>
      <dl className="grid min-w-0 gap-x-6 gap-y-3 sm:grid-cols-2">
        {[
          [
            'Scope',
            scope.area || scope.map_view_id || scope.map_origin
              ? 'Pinned saved area'
              : scope.country_isos.join(', ') || 'Worldwide',
          ],
          ['Subject', scope.subject ?? 'No additional subject'],
          ['Observation', period],
          [
            'Outlook',
            observation.forecast_horizon_days
              ? `${observation.forecast_horizon_days} days forward, separate from observed evidence`
              : 'No forecast requested',
          ],
          ['Depth', { quick: 'Basic', detailed: 'Deep', advanced: 'Advanced' }[draft.output.depth]],
          [
            'Questions',
            `${draft.question.requirements.filter((row) => row.required).length} required questions selected`,
          ],
          [
            'Perspective',
            `${draft.lens.id.replaceAll('_', ' ')}${draft.lens.audience ? ` · ${draft.lens.audience}` : ''}`,
          ],
          [
            'Language',
            `Report: ${draft.output.language}; collection: ${draft.collection.languages.join(', ')}`,
          ],
        ].map(([label, value]) => (
          <div key={label} className="min-w-0">
            <dt className="text-xs text-muted">{label}</dt>
            <dd className="mt-1 break-words">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="text-xs text-muted">
        Source coverage can be incomplete. Preview the saved revision in Depth before running.
      </p>
    </section>
  );
}
