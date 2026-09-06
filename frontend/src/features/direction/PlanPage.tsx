import { useCallback } from 'react';
import { Link, useNavigate, useParams } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { deletePlan, fetchPlanEvidence } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';

import { EventRow } from '../trackers/TrackerParts';
import { describeArea } from './DirectionPage';

export default function PlanPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const loader = useCallback(() => fetchPlanEvidence(id), [id]);
  const workspaces = useWorkspaces();
  const { data, error, loading } = useScopedResource(loader);
  const remove = useAsyncAction(async () => {
    await deletePlan(id);
    await navigate('/direction');
  });
  if (data === null) {
    return (
      <section className="p-6">
        {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
        {loading ? <LoadingNote label="Loading plan" /> : null}
      </section>
    );
  }
  const { plan, aoi, sirs } = data;
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
          <Link
            to={`/reports?template=ask&plan=${plan.id}`}
            className="rounded-md border border-line bg-surface-2 px-3 py-2 text-sm text-text hover:bg-surface"
          >
            Generate assessment
          </Link>
          <Button
            disabled={!workspaces.canManage(plan)}
            variant="danger"
            busy={remove.busy}
            onClick={() => void remove.run()}
          >
            Delete plan
          </Button>
        </div>
        {remove.error === null ? null : <Alert tone="error">{describeError(remove.error)}</Alert>}
      </header>
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
