import { useCallback, useRef } from 'react';
import type { RefObject } from 'react';

import { Alert as Notice, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { OwnershipScopeControl } from '@/components/workspace/OwnershipScopeControl';
import { describeError } from '@/lib/api/errors';
import { acknowledgeAlert, fetchAlerts } from '@/lib/api/warning';
import type { Alert } from '@/lib/api/warning';
import { formatAgo } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useConfirmedAction } from '@/lib/hooks/useConfirmedAction';
import type { ConfirmedAction } from '@/lib/hooks/useConfirmedAction';
import { useNow } from '@/lib/hooks/useNow';
import { useOwnershipScope } from '@/lib/hooks/useOwnershipScope';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { belongsToSomeoneElse, ownerLabel } from '@/lib/ownershipScope';
import type { OwnedRecord } from '@/lib/ownershipScope';

import { AlertDestination } from './AlertDestination';

const owned = (alert: Alert): OwnedRecord => ({
  team_id: alert.team_id,
  ownerId: alert.created_by,
  ownerName: alert.owner_name,
});

function AlertItem({
  alert,
  onAcknowledge,
  workspace,
  canAcknowledge,
  confirms,
}: {
  alert: Alert;
  onAcknowledge: () => void;
  workspace: string;
  canAcknowledge: boolean;
  /** Acknowledging asks first, because the alert is someone else's personal alert. */
  confirms: boolean;
}) {
  const now = useNow();
  return (
    <li className="flex flex-col gap-1 rounded-card border border-line bg-surface p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-medium">
          {alert.title}
          <span className="ml-2 text-xs text-muted">{workspace}</span>
        </span>
        <span className="font-mono text-xs text-muted">{formatAgo(alert.fired_at, now)}</span>
      </div>
      {alert.summary !== '' && <p className="text-xs text-muted">{alert.summary}</p>}
      <div className="flex flex-wrap items-center gap-3 text-xs">
        {alert.countries.length > 0 && (
          <span className="font-mono text-muted">{alert.countries.join(', ')}</span>
        )}
        <AlertDestination
          monitorId={alert.annotation_monitor_id}
          transitionId={alert.annotation_transition_id}
          reportId={alert.report_id}
        />
        {alert.acknowledged_at === null ? (
          <Button
            variant="secondary"
            disabled={!canAcknowledge}
            aria-haspopup={confirms ? 'dialog' : undefined}
            onClick={onAcknowledge}
          >
            Acknowledge
          </Button>
        ) : (
          <span className="text-muted">acknowledged</span>
        )}
      </div>
    </li>
  );
}

/** Acknowledgement is shared state, so clearing someone else's personal alert names them first. */
function SharedAcknowledgement({
  action,
  returnFocus,
}: {
  action: ConfirmedAction<Alert>;
  returnFocus: RefObject<HTMLElement | null>;
}) {
  const alert = action.target;
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
    async (id: string) => {
      const updated = await acknowledgeAlert(id);
      setAlerts((page) =>
        page === null
          ? page
          : {
              items: page.items.map((item) => (item.id === updated.id ? updated : item)),
              unacknowledged: Math.max(0, page.unacknowledged - 1),
            },
      );
    },
    [setAlerts],
  );
  const acknowledge = useAsyncAction(markAcknowledged);
  const shared = useConfirmedAction(
    useCallback((alert: Alert) => markAcknowledged(alert.id), [markAcknowledged]),
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
                onAcknowledge={() => (confirms ? shared.ask(item) : void acknowledge.run(item.id))}
              />
            );
          })}
        </ul>
      )}
      <SharedAcknowledgement action={shared} returnFocus={heading} />
    </div>
  );
}
