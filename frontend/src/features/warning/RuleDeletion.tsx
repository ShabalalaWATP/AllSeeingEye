import type { RefObject } from 'react';

import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { describeError } from '@/lib/api/errors';
import type { Indicator } from '@/lib/api/warning';
import type { ConfirmedAction } from '@/lib/hooks/useConfirmedAction';

/** Confirms deleting one alert rule, naming it, its workspace and what it watches. */
export function RuleDeletion({
  action,
  workspaceLabel,
  describe,
  returnFocus,
}: {
  action: ConfirmedAction<Indicator>;
  workspaceLabel: (teamId: string | null) => string;
  describe: (rule: Indicator) => string;
  returnFocus: RefObject<HTMLElement | null>;
}) {
  const rule = action.target;
  return (
    <ConfirmDialog
      open={rule !== null}
      title={`Delete alert rule “${rule?.name ?? ''}”?`}
      confirmLabel="Delete rule"
      busyLabel="Deleting rule…"
      busy={action.busy}
      error={action.error === null ? null : describeError(action.error)}
      returnFocus={returnFocus}
      onCancel={action.cancel}
      onConfirm={action.confirm}
    >
      {rule === null ? null : (
        <>
          <p>
            <span className="font-medium text-text">Workspace:</span>{' '}
            {workspaceLabel(rule.team_id ?? null)}
          </p>
          <p>
            <span className="font-medium text-text">Watches:</span> {describe(rule)}
          </p>
          <p>
            Deleting the rule permanently stops raising new alerts for it. Alerts it has already
            raised are kept.
          </p>
          <p className="font-medium text-critical">This cannot be undone.</p>
        </>
      )}
    </ConfirmDialog>
  );
}
