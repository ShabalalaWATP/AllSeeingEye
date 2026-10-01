import { useCallback, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';

import { RequirementCodesNote } from '@/components/ui/RequirementCodesNote';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { deletePlan, fetchAois, fetchPlanEvidence } from '@/lib/api/direction';
import type { AreaOfInterest, CollectionPlan } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import { useConfirmedAction } from '@/lib/hooks/useConfirmedAction';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';

import { EventRow } from '@/components/events/EventRow';
import { describeArea } from './DirectionPage';
import { PlanDeletion } from './DirectionDeletions';
import { PlanForm } from './PlanForm';
import { ResearchAreaButton } from './ResearchAreaButton';

interface EditSession {
  plan: CollectionPlan;
  areas: readonly AreaOfInterest[];
}

export default function PlanPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const loader = useCallback(() => fetchPlanEvidence(id), [id]);
  const workspaces = useWorkspaces();
  const { data, error, loading, refresh } = useScopedResource(loader);
  const areas = useScopedResource(fetchAois);
  const [editing, setEditing] = useState<EditSession | null>(null);
  const remove = useConfirmedAction(
    useCallback(
      async (plan: CollectionPlan) => {
        await deletePlan(plan.id);
        await navigate('/direction');
      },
      [navigate],
    ),
  );
  // Rendered in every state, so a refusal that reloads the plan keeps its confirmation open.
  const confirmation = <PlanDeletion action={remove} workspaceLabel={workspaces.label} />;
  // The editor keeps its second slot in both renders below while the plan reloads after an access recheck, so a refused
  // save keeps the draft. A failed reload (lost access) unmounts it and drops the draft.
  const editor =
    editing !== null && error === null ? (
      <PlanForm
        key={editing.plan.id}
        areas={editing.areas}
        workspaces={workspaces}
        plan={editing.plan}
        onSaved={async () => {
          setEditing(null);
          await refresh();
        }}
        onCancel={() => setEditing(null)}
      />
    ) : null;
  if (data === null) {
    return (
      <article className="flex flex-col gap-5 p-6">
        <div>
          {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
          {loading ? <LoadingNote label="Loading plan" /> : null}
        </div>
        {editor}
        {confirmation}
      </article>
    );
  }
  const { plan, aoi, sirs } = data;
  const manageable = workspaces.canManage(plan);
  return (
    <article className="flex h-full flex-col gap-5 overflow-y-auto p-6">
      <header className="flex flex-col gap-2">
        <Link to="/direction" className="text-xs text-muted hover:underline">
          Direction
        </Link>
        <h1 className="text-xl font-semibold">{plan.name}</h1>
        <p className="text-xs text-muted">{workspaces.label(plan.team_id)}</p>
        {plan.description !== '' && <p className="text-sm text-muted">{plan.description}</p>}
        <p className="font-mono text-xs text-muted">
          {aoi !== null ? `${aoi.name} (${describeArea(aoi)})` : 'no area'}
          {plan.countries.length > 0 ? ` · ${plan.countries.join(', ')}` : ''} · {data.considered}{' '}
          items considered
        </p>
        <div className="flex flex-wrap gap-2">
          {aoi && (
            <Link
              to={`/?area=${encodeURIComponent(aoi.id)}`}
              className="rounded-md border border-line bg-surface-2 px-3 py-2 text-sm text-text hover:bg-surface"
            >
              Open area on map
            </Link>
          )}
          {aoi?.research_area ? (
            <div>
              <ResearchAreaButton area={aoi} />
              <p className="text-xs text-muted">
                Opens standalone personal area research. Plan requirements are not transferred; add
                your question in the research form.
              </p>
            </div>
          ) : (
            <div>
              <Link
                to={`/research?brief=new&plan=${encodeURIComponent(plan.id)}`}
                className="inline-block rounded-md border border-line bg-surface-2 px-3 py-2 text-sm text-text hover:bg-surface"
              >
                Generate assessment
              </Link>
              <p className="text-xs text-muted">
                Opens Research to review this plan&apos;s requirements (
                {workspaces.label(plan.team_id)}). Nothing runs until you start it.
              </p>
            </div>
          )}
          <Button
            variant="secondary"
            disabled={!manageable || editing !== null || areas.data === null}
            onClick={() => {
              if (areas.data !== null) setEditing({ plan, areas: areas.data });
            }}
          >
            Edit plan
          </Button>
          <Button
            disabled={!manageable}
            variant="danger"
            aria-haspopup="dialog"
            onClick={() => remove.ask(plan)}
          >
            Delete plan
          </Button>
        </div>
        {areas.error !== null && manageable && (
          <Alert tone="error">
            Areas could not be loaded, so the plan cannot be edited yet.{' '}
            <Button variant="secondary" onClick={() => void areas.reload()}>
              Retry areas
            </Button>
          </Alert>
        )}
        {confirmation}
      </header>
      {editor}
      <RequirementCodesNote codes={['PIR', 'SIR']} />
      {plan.pirs.map((pir) => (
        <section key={pir.code} aria-label={pir.code} className="flex flex-col gap-3">
          <h2 className="text-base font-semibold">
            <span className="mr-2 font-mono text-xs text-muted">{pir.code}</span>
            {pir.text}
          </h2>
          {pir.sirs.map((sir) => {
            const evidence = sirs.find((row) => row.code === sir.code);
            return (
              <div key={sir.code} className="rounded-card border border-line bg-surface p-3">
                <h3 className="text-sm font-medium">
                  <span className="mr-2 font-mono text-xs text-muted">{sir.code}</span>
                  {sir.text}
                </h3>
                <p className="mt-1 font-mono text-[11px] text-muted">
                  {sir.keywords.length > 0 ? `keywords: ${sir.keywords.join(', ')}` : 'no keywords'}
                  {sir.categories.length > 0 ? ` · ${sir.categories.join(', ')}` : ''}
                </p>
                {evidence === undefined || evidence.events.length === 0 ? (
                  <p className="mt-2 text-xs text-muted">Nothing gathered in the last week.</p>
                ) : (
                  <ul className="mt-2">
                    {evidence.events.map((event) => (
                      <EventRow key={event.id} event={event} />
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </section>
      ))}
    </article>
  );
}
