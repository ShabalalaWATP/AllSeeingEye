import type { RefObject } from 'react';
import { Link } from 'react-router';

import { Button } from '@/components/ui/Button';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type { BellAlert } from '@/lib/api/bell';
import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';

import { ALERTS_PAGE } from './useBellAlertActions';
import type { BellAlertActions, BellNotice } from './useBellAlertActions';
import type { NotificationBellState } from './useNotificationBell';

export const headingClass = 'px-2 font-mono text-xs tracking-widest text-muted uppercase';
const openClass =
  'block w-full rounded-md px-2 py-2 text-left hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-ember disabled:opacity-60';
const smallButton = 'min-h-11 px-2 text-xs';

function NoticeText({ notice, actions }: { notice: BellNotice; actions: BellAlertActions }) {
  return (
    <div
      className={`mx-2 mt-1 rounded-md border px-2 py-1.5 text-xs ${
        notice.tone === 'error' ? 'border-critical/50 text-critical' : 'border-line text-muted'
      }`}
    >
      <p>{notice.text}</p>
      <div className="mt-1 flex flex-wrap gap-x-3">
        {notice.alertId !== null && (
          <Link to={ALERTS_PAGE} className="text-ember underline-offset-2 hover:underline">
            Open Alerts
          </Link>
        )}
        {notice.undoRule && (
          <Button
            variant="ghost"
            className={smallButton}
            busy={actions.pending.has(`rule:${notice.undoRule.id}`)}
            onClick={() => notice.undoRule && actions.undoMute(notice.undoRule.id)}
          >
            Undo mute
          </Button>
        )}
        <Button variant="ghost" className={smallButton} onClick={actions.dismissNotice}>
          Dismiss
        </Button>
      </div>
    </div>
  );
}

function AlertRow({ alert, actions }: { alert: BellAlert; actions: BellAlertActions }) {
  const busy = actions.pending.has(alert.id);
  const notice = actions.notice?.alertId === alert.id ? actions.notice : null;
  const workspace = alert.team_name
    ? `Team: ${alert.team_name}, acknowledgement is shared`
    : 'Personal';
  return (
    <li className="border-b border-line/60 py-1 last:border-b-0" aria-busy={busy}>
      <button
        type="button"
        className={openClass}
        disabled={busy}
        onClick={() => actions.open(alert)}
      >
        <span className="block text-sm text-text">{alert.title}</span>
        <span className="mt-0.5 block text-xs text-muted">
          {workspace} · Fired {formatUtc(alert.fired_at)}
        </span>
      </button>
      <div className="flex flex-wrap gap-1 px-1">
        {alert.can_acknowledge ? (
          <Button
            variant="ghost"
            className={smallButton}
            busy={busy}
            busyLabel="Acknowledging…"
            aria-label={`Acknowledge ${alert.title}`}
            onClick={() => actions.acknowledge(alert)}
          >
            Acknowledge
          </Button>
        ) : (
          <span className="px-2 py-1 text-xs text-muted">
            Read-only: this team is archived or you cannot acknowledge it.
          </span>
        )}
        {alert.indicator_id !== null && (
          <Button
            variant="ghost"
            className={smallButton}
            disabled={busy}
            aria-label={`Mute this rule in my bell: ${alert.title}`}
            onClick={() => actions.mute(alert)}
          >
            Mute rule
          </Button>
        )}
      </div>
      {notice && <NoticeText notice={notice} actions={actions} />}
    </li>
  );
}

/** Unacknowledged alerts with in-place opening, acknowledgement and rule muting. */
export function BellAlertList({
  state,
  actions,
  headingRef,
  returnFocus,
}: {
  state: NotificationBellState;
  actions: BellAlertActions;
  headingRef: RefObject<HTMLHeadingElement | null>;
  returnFocus: RefObject<HTMLElement | null>;
}) {
  const { alerts, windowDays } = state;
  const eligible = alerts.items.filter((item) => item.can_acknowledge);
  const shown = actions.acknowledgeShown;
  const listNotice = actions.notice?.alertId === null ? actions.notice : null;
  const teamShown = (shown.target ?? []).some((item) => item.team_id !== null);
  return (
    <section aria-labelledby="bell-alerts-heading">
      <h3 id="bell-alerts-heading" ref={headingRef} tabIndex={-1} className={headingClass}>
        Alerts to review · last {windowDays} days
      </h3>
      {alerts.error ? (
        <p className="px-2 pt-1 text-sm text-muted">Alerts could not be loaded.</p>
      ) : (
        <ul className="mt-1" aria-label="Unacknowledged alerts">
          {alerts.items.map((alert) => (
            <AlertRow key={alert.id} alert={alert} actions={actions} />
          ))}
        </ul>
      )}
      {listNotice && <NoticeText notice={listNotice} actions={actions} />}
      {alerts.total > alerts.items.length && (
        <p className="px-2 pt-1 text-xs text-muted">
          {alerts.total - alerts.items.length} more in the last {windowDays} days on the Alerts
          page.
        </p>
      )}
      <p className="px-2 pt-1 text-xs text-muted">
        Alerts older than {windowDays} days are not listed here, whether or not anyone acknowledged
        them.
      </p>
      {eligible.length > 1 && (
        <Button
          variant="secondary"
          className="mx-2 mt-2 min-h-11"
          onClick={() => shown.ask(eligible)}
        >
          Acknowledge {eligible.length} shown
        </Button>
      )}
      <ConfirmDialog
        open={shown.target !== null}
        title={`Acknowledge ${String(shown.target?.length ?? 0)} shown alerts?`}
        confirmLabel="Acknowledge shown"
        busyLabel="Acknowledging…"
        tone="primary"
        busy={shown.busy}
        error={shown.error ? describeError(shown.error) : null}
        onConfirm={shown.confirm}
        onCancel={shown.cancel}
        returnFocus={returnFocus}
      >
        <p>Only these alerts are acknowledged:</p>
        <ul className="mt-2 list-disc pl-5">
          {(shown.target ?? []).map((item) => (
            <li key={item.id}>{item.title}</li>
          ))}
        </ul>
        <p className="mt-2">
          Alerts further down the Alerts page, alerts hidden by your bell settings and finished
          research are not changed.
          {teamShown ? ' Acknowledging a team alert clears it for everyone in that team.' : ''}
        </p>
      </ConfirmDialog>
    </section>
  );
}
