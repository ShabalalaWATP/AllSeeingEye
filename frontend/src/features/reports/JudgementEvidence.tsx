import type { JudgementAssessment } from '@/lib/api/reportAssessment';

import { Labels } from './EvidenceLinks';

const balanceLabels: Record<JudgementAssessment['balance'], string> = {
  no_support: 'No eligible support',
  support_only: 'No opposition assigned to this judgement',
  support_stronger: 'Support stronger than opposition',
  opposition_at_least_as_strong: 'Opposition at least as strong as support',
};

function GroupList({
  title,
  tier,
  groups,
  labels,
}: {
  title: string;
  tier: JudgementAssessment['support_tier'];
  groups: JudgementAssessment['support_groups'];
  labels: string[];
}) {
  return (
    <div className="min-w-0">
      <h4 className="text-xs font-medium">
        {title}: <span className="font-mono">{tier}</span>
      </h4>
      <p className="mt-1 text-xs text-muted">
        {groups.length} contribution {groups.length === 1 ? 'group' : 'groups'}
        {labels.length > 0 && <Labels labels={labels} />}
      </p>
      <p className="mt-1 text-xs text-muted">
        {groups.filter((group) => group.known_organisation).length} declared organisation groups ·{' '}
        {groups.filter((group) => group.possible_copy).length} possible-copy groups
      </p>
      {groups.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs text-muted">
          {groups.map((group) => (
            <li key={group.id}>
              {group.contribution} ·{' '}
              {group.known_organisation ? 'Declared organisation' : 'Unknown organisation'}
              {group.possible_copy && ' · Possible copy'}
              <Labels labels={group.labels} />
              {group.corroborating_contribution !== group.contribution && (
                <span className="block">
                  Eligible for corroboration: {group.corroborating_contribution}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Notes({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h4 className="text-xs font-medium">{title}</h4>
      <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-muted">
        {items.map((text) => (
          <li key={text}>{text}</li>
        ))}
      </ul>
    </div>
  );
}

/** Display the saved engine decision; never infer a new confidence rating in the browser. */
export function JudgementEvidence({ assessment }: { assessment: JudgementAssessment }) {
  return (
    <section
      aria-label={`Evidence assessment for ${assessment.judgement_id}`}
      className="mt-4 border-t border-line pt-3"
    >
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs">
        <h3 className="font-medium capitalize">
          {assessment.status === 'unsupported'
            ? 'No assessed support'
            : `${assessment.status} judgement`}
        </h3>
        <p className="text-muted">{balanceLabels[assessment.balance]}</p>
      </div>
      <p className="mt-2 text-xs text-muted">
        Supporting: {assessment.support_tier} · Opposing: {assessment.opposition_tier}
      </p>
      <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
        <div>
          <dt className="text-muted">Confidence ceiling</dt>
          <dd className="mt-1 font-mono capitalize">{assessment.confidence_ceiling}</dd>
        </div>
        <div>
          <dt className="text-muted">Final confidence</dt>
          <dd className="mt-1 font-mono capitalize">{assessment.final_confidence}</dd>
        </div>
      </dl>
      <details className="mt-2">
        <summary className="cursor-pointer py-2 text-xs text-ember">
          Why this evidence rating?
        </summary>
        <div className="mt-2 flex flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <GroupList
              title="Supporting strength"
              tier={assessment.support_tier}
              groups={assessment.support_groups}
              labels={assessment.supporting_labels}
            />
            <GroupList
              title="Opposing strength"
              tier={assessment.opposition_tier}
              groups={assessment.opposition_groups}
              labels={assessment.contradicting_labels}
            />
          </div>
          <p className="text-xs text-muted">
            These relationships were assigned to this judgement by the model. Each declared
            organisation or possible-copy group contributes once; these groups do not verify
            independent sourcing. Separate devil's advocacy is shown below when recorded.
          </p>
          <Notes title="Why" items={assessment.explanation} />
          <Notes title="Limitations" items={assessment.limitations} />
          <Notes title="What would improve confidence" items={assessment.improvements} />
          {assessment.invalid_labels.length > 0 && (
            <p className="text-xs text-amber">
              Unavailable citations: {assessment.invalid_labels.join(', ')}
            </p>
          )}
        </div>
      </details>
    </section>
  );
}
