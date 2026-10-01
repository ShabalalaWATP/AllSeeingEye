import { useCallback, useRef } from 'react';
import type { RefObject } from 'react';

import { Alert as Notice, LoadingNote } from '@/components/ui/Alert';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { OwnershipScopeControl } from '@/components/workspace/OwnershipScopeControl';
import { describeError } from '@/lib/api/errors';
import { acknowledgeAlert, fetchAlerts } from '@/lib/api/warning';
import type { Alert, AlertAcknowledgementRequest } from '@/lib/api/warning';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useConfirmedAction } from '@/lib/hooks/useConfirmedAction';
import type { ConfirmedAction } from '@/lib/hooks/useConfirmedAction';
import { useOwnershipScope } from '@/lib/hooks/useOwnershipScope';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { belongsToSomeoneElse, ownerLabel } from '@/lib/ownershipScope';
import type { OwnedRecord } from '@/lib/ownershipScope';

import { AlertItem } from './AlertItem';

const owned = (alert: Alert): OwnedRecord => ({
  team_id: alert.team_id,
  ownerId: alert.created_by,
  ownerName: alert.owner_name,
});

interface PendingAcknowledgement {
  alert: Alert;
  feedback: AlertAcknowledgementRequest;
}

/** Acknowledgement is shared state, so clearing someone else's personal alert names them first. */
function SharedAcknowledgement({
  action,
  returnFocus,
}: {
  action: ConfirmedAction<PendingAcknowledgement>;
  returnFocus: RefObject<HTMLElement | null>;
}) {
  const alert = action.target?.alert ?? null;
  const owner = alert?.owner_name ?? 'another user';
  return (
    <ConfirmDialog
      open={alert !== null}
      title={`Acknowledge ${owner}'s personal alert?`}
      confirmLabel="Acknowledge for everyone"
      busyLabel="Acknowledging…"
      tone="primary"
      busy={action.busy}
      error={action.error === null ? null : describeError(action.error)}
      returnFocus={returnFocus}
      onCancel={action.cancel}
      onConfirm={action.confirm}
    >
      {alert === null ? null : (
        <>
          <p>
            “{alert.title}” belongs to {owner}&apos;s personal workspace, not yours.
          </p>
          <p>Acknowledgement is shared: acknowledging it here also clears it for {owner}.</p>
        </>
      )}
    </ConfirmDialog>
  );
}

/** Alerts in the selected ownership scope. The shell's bell always keeps its own default. */
export function AlertsSection({ workspaces }: { workspaces: Workspaces }) {
  const ownership = useOwnershipScope();
  const { scope, viewerId } = ownership;
  const load = useCallback(() => fetchAlerts(undefined, undefined, scope), [scope]);
  const alerts = useScopedResource(load);
  const setAlerts = alerts.setData;
  const heading = useRef<HTMLHeadingElement>(null);

  const markAcknowledged = useCallback(
    async (id: string, feedback: AlertAcknowledgementRequest) => {
      const updated = await acknowledgeAlert(id, feedback);
      setAlerts((page) =>
        page === null
          ? page
          : {
              items: page.items.map((item) =>
                item.id === updated.id ? { ...updated, owner_name: item.owner_name } : item,
              ),
              unacknowledged: Math.max(0, page.unacknowledged - 1),
            },
      );
    },
    [setAlerts],
  );
  const acknowledge = useAsyncAction(markAcknowledged);
  const shared = useConfirmedAction(
    useCallback(
      ({ alert, feedback }: PendingAcknowledgement) => markAcknowledged(alert.id, feedback),
      [markAcknowledged],
    ),
  );

  return (
    <div className="flex flex-col gap-3">
      <h2 ref={heading} className="text-base font-semibold">
        Alerts
      </h2>
      <OwnershipScopeControl state={ownership} noun="alerts" />
      {alerts.error === null ? null : <Notice tone="error">{describeError(alerts.error)}</Notice>}
      {acknowledge.error === null ? null : (
        <Notice tone="error">{describeError(acknowledge.error)}</Notice>
      )}
      {alerts.data === null ? (
        alerts.loading ? (
          <LoadingNote label="Loading alerts" />
        ) : null
      ) : alerts.data.items.length === 0 ? (
        <p className="text-sm text-muted">Nothing has fired in the last week.</p>
      ) : (
        <ul aria-label="Alerts" className="flex flex-col gap-2">
          {alerts.data.items.map((item) => {
            const confirms = belongsToSomeoneElse(owned(item), viewerId);
            return (
              <AlertItem
                key={item.id}
                alert={item}
                workspace={ownerLabel(owned(item), workspaces.label, viewerId)}
                canAcknowledge={workspaces.canAcknowledge(item.team_id)}
                confirms={confirms}
                onAcknowledge={(feedback) =>
                  confirms
                    ? shared.ask({ alert: item, feedback })
                    : void acknowledge.run(item.id, feedback)
                }
              />
            );
          })}
        </ul>
      )}
      <SharedAcknowledgement action={shared} returnFocus={heading} />
    </div>
  );
}
