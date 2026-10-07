import type { RefObject } from 'react';

import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type { AreaOfInterest, CollectionPlan } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import type { ConfirmedAction } from '@/lib/hooks/useConfirmedAction';

type WorkspaceLabel = (teamId: string | null) => string;

function errorText<T>(action: ConfirmedAction<T>): string | null {
  return action.error === null ? null : describeError(action.error);
}

/** Confirms deleting a saved area, naming it, its workspace and its extent. */
export function AreaDeletion({
  action,
  workspaceLabel,
  describe,
  returnFocus,
}: {
  action: ConfirmedAction<AreaOfInterest>;
  workspaceLabel: WorkspaceLabel;
  describe: (area: AreaOfInterest) => string;
  returnFocus: RefObject<HTMLElement | null>;
}) {
  const area = action.target;
  return (
    <ConfirmDialog
      open={area !== null}
      title={`Delete area “${area?.name ?? ''}”?`}
      confirmLabel="Delete area"
      busyLabel="Deleting area…"
      busy={action.busy}
      error={errorText(action)}
      returnFocus={returnFocus}
      onCancel={action.cancel}
      onConfirm={action.confirm}
    >
      {area === null ? null : (
        <>
          <p>
            <span className="font-medium text-text">Workspace:</span>{' '}
            {workspaceLabel(area.team_id ?? null)}
          </p>
          <p>
            <span className="font-medium text-text">Extent:</span> {describe(area)}
          </p>
          <p>
            This permanently deletes the saved area and removes it from any collection plans that
            use it. Plans that use this area keep their requirements and will need a new area.
          </p>
          <p className="font-medium text-critical">This cannot be undone.</p>
        </>
      )}
    </ConfirmDialog>
  );
}

/** Confirms deleting a collection plan, naming it, its workspace and its requirements. */
export function PlanDeletion({
  action,
  workspaceLabel,
}: {
  action: ConfirmedAction<CollectionPlan>;
  workspaceLabel: WorkspaceLabel;
}) {
  const plan = action.target;
  const specific = plan?.pirs.reduce((total, pir) => total + pir.sirs.length, 0) ?? 0;
  return (
    <ConfirmDialog
      open={plan !== null}
      title={`Delete collection plan “${plan?.name ?? ''}”?`}
      confirmLabel="Delete plan"
      busyLabel="Deleting plan…"
      busy={action.busy}
      error={errorText(action)}
      onCancel={action.cancel}
      onConfirm={action.confirm}
    >
      {plan === null ? null : (
        <>
          <p>
            <span className="font-medium text-text">Workspace:</span>{' '}
            {workspaceLabel(plan.team_id ?? null)}
          </p>
          <p>
            This permanently deletes the plan with its {plan.pirs.length} priority and {specific}{' '}
            specific requirement{plan.pirs.length + specific === 1 ? '' : 's'}. Saved areas, alert
            rules and reports are kept.
          </p>
          <p className="font-medium text-critical">This cannot be undone.</p>
        </>
      )}
    </ConfirmDialog>
  );
}
