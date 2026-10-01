import { useCallback, useRef } from 'react';
import { Link } from 'react-router';

import { DiscussWithTeamLink } from '@/components/teams/DiscussWithTeamLink';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { Table, Td, Th } from '@/components/ui/Table';
import { deleteAoi, fetchAois, fetchPlans } from '@/lib/api/direction';
import type { AreaOfInterest } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import { mapPanelHref } from '@/lib/mapLayerDirectory';
import { useConfirmedAction } from '@/lib/hooks/useConfirmedAction';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';

import { AreaForm } from './AreaForm';
import { AreaDeletion } from './DirectionDeletions';
import { ResearchAreaButton } from './ResearchAreaButton';
import { PlanForm } from './PlanForm';

export function describeArea(area: AreaOfInterest): string {
  if (area.research_area) return `exact shape · ${area.research_area.sha256.slice(0, 12)}`;
  if (area.kind === 'bbox' && area.bbox !== null) {
    return `box ${area.bbox.map((n) => n.toFixed(1)).join(', ')}`;
  }
  return `nations ${area.countries.join(', ')}`;
}

export default function DirectionPage() {
  const workspaces = useWorkspaces();
  const areas = useScopedResource(fetchAois);
  const plans = useScopedResource(fetchPlans);
  const reloadAreas = areas.reload;
  const reloadPlans = plans.reload;
  const areasHeading = useRef<HTMLHeadingElement>(null);
  const remove = useConfirmedAction(
    useCallback(
      async (area: AreaOfInterest) => {
        await deleteAoi(area.id);
        await reloadAreas();
      },
      [reloadAreas],
    ),
  );
  return (
    <section className="flex h-full flex-col gap-6 overflow-y-auto p-6">
      <h1 className="text-xl font-semibold">Plans and areas</h1>
      <p className="text-sm text-muted">
        Save reusable geographic areas and structured questions for more detailed research. Open
        saved areas on the map, or reuse them in{' '}
        <Link to="/subscriptions" className="text-text underline">
          Subscriptions
        </Link>
        . Save a drawn map area from the Research area tool. For a one-off question, use{' '}
        <Link to="/research" className="text-text underline">
          Research
        </Link>
        .
      </p>
      <div className="flex flex-col gap-3">
        <h2 ref={areasHeading} className="text-base font-semibold">
          Areas of interest
        </h2>
        {areas.error === null ? null : <Alert tone="error">{describeError(areas.error)}</Alert>}
        {areas.data === null ? (
          areas.loading ? (
            <LoadingNote label="Loading areas" />
          ) : null
        ) : areas.data.length === 0 ? (
          <EmptyState
            title="No areas of interest yet"
            purpose="An area of interest is a saved place you can reuse in research, subscriptions and collection plans."
            action={
              <Link to={mapPanelHref('Research area')} className="text-ember underline">
                Draw an area on the map
              </Link>
            }
          />
        ) : (
          <Table caption="Areas of interest">
            <thead>
              <tr>
                <Th>Area</Th>
                <Th>Extent</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {areas.data.map((area) => (
                <tr key={area.id}>
                  <Td className="font-medium">
                    {area.name}
                    <div className="text-xs text-muted">{workspaces.label(area.team_id)}</div>
                  </Td>
                  <Td className="font-mono text-xs text-muted">{describeArea(area)}</Td>
                  <Td>
                    <ResearchAreaButton area={area} />
                    <Link
                      to={`/?area=${encodeURIComponent(area.id)}`}
                      className="mr-3 text-sm text-ember hover:underline"
                    >
                      Open on map
                    </Link>
                    <DiscussWithTeamLink
                      teamId={area.team_id}
                      subject={{ kind: 'saved_area', id: area.id }}
                      className="mr-3 text-sm text-ember hover:underline"
                    />
                    <Button
                      disabled={!workspaces.canManage(area)}
                      variant="danger"
                      aria-haspopup="dialog"
                      onClick={() => remove.ask(area)}
                    >
                      Delete
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
        <AreaDeletion
          action={remove}
          workspaceLabel={workspaces.label}
          describe={describeArea}
          returnFocus={areasHeading}
        />
        <AreaForm key={workspaces.key} workspaces={workspaces} onCreated={reloadAreas} />
      </div>
      <div className="flex flex-col gap-3">
        <h2 className="text-base font-semibold">Collection plans</h2>
        {plans.error === null ? null : <Alert tone="error">{describeError(plans.error)}</Alert>}
        {plans.data === null ? (
          plans.loading ? (
            <LoadingNote label="Loading plans" />
          ) : null
        ) : plans.data.length === 0 ? (
          <EmptyState
            title="No collection plans yet"
            purpose="A collection plan sets out intelligence requirements and gathers matching evidence from the live feeds as it arrives."
            action="Write your first plan with the form below."
          />
        ) : (
          <ul aria-label="Collection plans" className="flex flex-col gap-2">
            {plans.data.map((plan) => (
              <li key={plan.id} className="rounded-card border border-line bg-surface p-3">
                <Link
                  to={`/direction/plans/${plan.id}`}
                  className="font-medium text-text hover:underline"
                >
                  {plan.name}
                </Link>
                <p className="text-xs text-muted">{workspaces.label(plan.team_id)}</p>
                <p className="mt-1 text-xs text-muted">
                  {plan.pirs.length} PIR, {plan.pirs.reduce((n, pir) => n + pir.sirs.length, 0)} SIR
                  {plan.countries.length > 0 ? ` · ${plan.countries.join(', ')}` : ''}
                </p>
              </li>
            ))}
          </ul>
        )}
        <PlanForm
          key={workspaces.key}
          workspaces={workspaces}
          areas={areas.data ?? []}
          onSaved={reloadPlans}
        />
      </div>
    </section>
  );
}
