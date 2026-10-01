import { RequirementCodesNote } from '@/components/ui/RequirementCodesNote';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';

import type { BriefPlan } from './useBriefPlan';

/** The collection plan a brief is scoped by, shown for review before research starts. */
export function BriefPlanContext({ state }: { state: BriefPlan }) {
  const workspaces = useWorkspaces();
  const { plan, blocker, loading } = state;
  return (
    <section
      aria-label="Collection plan"
      className="space-y-3 rounded-card border border-line bg-surface p-4 text-sm"
    >
      <h3 className="font-semibold">Collection plan{plan ? `: ${plan.name}` : ''}</h3>
      {loading && plan === null && <LoadingNote label="Loading the collection plan" />}
      {plan && (
        <>
          <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
            <div>
              <dt className="text-muted">Workspace</dt>
              <dd>{workspaces.label(plan.team_id)}</dd>
            </div>
            <div>
              <dt className="text-muted">Effective scope</dt>
              <dd>
                {plan.aoi_id
                  ? "The plan's saved area"
                  : plan.countries.length > 0
                    ? `Nations: ${plan.countries.join(', ')}`
                    : 'Worldwide; the plan has no area or nations'}
              </dd>
            </div>
          </dl>
          <RequirementCodesNote codes={['PIR', 'SIR']} />
          <ol className="space-y-2">
            {plan.pirs.map((pir) => (
              <li key={pir.code}>
                <p>
                  <span className="mr-2 font-mono text-xs text-muted">{pir.code}</span>
                  {pir.text}
                </p>
                <ul className="mt-1 space-y-1 pl-5">
                  {pir.sirs.map((sir) => (
                    <li key={sir.code} className="text-muted">
                      <span className="mr-2 font-mono text-xs">{sir.code}</span>
                      {sir.text}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
          <p className="text-xs text-muted">
            Each requirement above becomes a brief question you can edit. Every specific
            requirement&apos;s keywords and categories, and the plan&apos;s area or nations, direct
            collection from the saved plan. Starting research checks this exact plan version again;
            if the plan changes while research waits, the job stops rather than widening its scope.
          </p>
        </>
      )}
      {blocker !== null && !(loading && plan === null) && (
        <Alert tone="warning" title="Research cannot start from this plan yet">
          {blocker}
        </Alert>
      )}
      <Button variant="secondary" busy={loading} onClick={() => void state.reload()}>
        Reload plan
      </Button>
    </section>
  );
}
