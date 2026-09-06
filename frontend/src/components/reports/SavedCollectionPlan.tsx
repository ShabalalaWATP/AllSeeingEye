import type { ResearchPlan } from '@/lib/api/researchPlan';

/** Frozen inputs remain separate from the receipt's actual collection outcomes. */
export function SavedCollectionPlan({ plan }: { plan: ResearchPlan }) {
  return (
    <section className="space-y-3 border-y border-line py-4" aria-label="Saved collection plan">
      <h3 className="text-sm font-medium">Saved collection plan</h3>
      <p className="text-xs text-muted">
        The plan recorded when this version was collected. Attempt results below show what happened.
      </p>
      <p className="text-xs">
        Limits: {plan.request_limit} requests, {plan.seconds_limit} seconds, {plan.item_limit}{' '}
        items.
      </p>
      <ul className="divide-y divide-line text-xs">
        {plan.tasks.map((task, index) => (
          <li className="space-y-1 py-2" key={`${task.source_id}:${task.language ?? ''}:${index}`}>
            <p className="font-medium">
              {task.source_name} · {task.language ?? 'Language-independent'} ·{' '}
              {task.selected ? 'Selected' : 'Excluded'}
            </p>
            <p className="break-words text-muted" dir="auto">
              {task.terms.join(' · ') || 'No search terms recorded'}
            </p>
            <p className="text-muted">
              {task.provenance === 'operator_supplied_variant'
                ? 'Operator-supplied language terms'
                : 'Original terms'}{' '}
              · {task.temporal_scope}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
