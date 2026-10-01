import { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router';

import { annotationTransitionHref } from '@/lib/annotationMonitorLinks';
import { acknowledgeAlerts, fetchAlertDestination, muteRule, unmuteRule } from '@/lib/api/bell';
import type { AlertDestination, Bell, BellAlert } from '@/lib/api/bell';
import { describeError, isApiError } from '@/lib/api/errors';
import { useConfirmedAction } from '@/lib/hooks/useConfirmedAction';
import type { ConfirmedAction } from '@/lib/hooks/useConfirmedAction';

import type { NotificationBellState } from './useNotificationBell';

export const ALERTS_PAGE = '/warning';
const GONE = 'This alert is no longer available to your account. It may have been removed.';

/** A message tied to one alert, or to the whole list when `alertId` is null. */
export interface BellNotice {
  alertId: string | null;
  tone: 'error' | 'info';
  text: string;
  /** Rule mute that can be undone from this notice. */
  undoRule?: { id: string; name: string } | undefined;
}

export interface BellAlertActions {
  /** Alert IDs with an open or acknowledge request in flight. */
  pending: ReadonlySet<string>;
  notice: BellNotice | null;
  dismissNotice: () => void;
  open: (alert: BellAlert) => void;
  acknowledge: (alert: BellAlert) => void;
  mute: (alert: BellAlert) => void;
  undoMute: (ruleId: string) => void;
  /** "Acknowledge shown", held behind a confirmation naming exactly these alerts. */
  acknowledgeShown: ConfirmedAction<BellAlert[]>;
}

export function destinationHref(destination: AlertDestination): string | null {
  if (!destination.available) return null;
  if (destination.kind === 'report' && destination.report_id !== null)
    return `/reports/${encodeURIComponent(destination.report_id)}`;
  if (
    destination.kind === 'transition' &&
    destination.monitor_id !== null &&
    destination.transition_id !== null
  )
    return annotationTransitionHref(destination.monitor_id, destination.transition_id);
  return destination.kind === 'alerts' ? ALERTS_PAGE : null;
}

function withoutAlerts(ids: ReadonlySet<string>) {
  return (bell: Bell): Bell => {
    const items = bell.alerts.items.filter((item) => !ids.has(item.id));
    const removed = bell.alerts.items.length - items.length;
    return { ...bell, alerts: { ...bell.alerts, items, total: bell.alerts.total - removed } };
  };
}

/**
 * Bell alert actions. Each request is sent at most once at a time per alert; a failure
 * leaves the item and count unchanged and says how to retry. The server authorises every
 * request again, and the bell refetches afterwards to reconcile with other sessions.
 */
export function useBellAlertActions(
  state: NotificationBellState,
  onItemsRemoved: () => void,
): BellAlertActions {
  const navigate = useNavigate();
  const [pending, setPending] = useState<ReadonlySet<string>>(new Set());
  const [notice, setNotice] = useState<BellNotice | null>(null);
  const inFlight = useRef(new Set<string>());
  const { close, refresh, updateBell, alerts } = state;

  const track = useCallback(async (ids: string[], work: () => Promise<void>) => {
    if (ids.some((id) => inFlight.current.has(id))) return;
    for (const id of ids) inFlight.current.add(id);
    setPending(new Set(inFlight.current));
    try {
      await work();
    } finally {
      for (const id of ids) inFlight.current.delete(id);
      setPending(new Set(inFlight.current));
    }
  }, []);

  const send = useCallback(
    async (targets: BellAlert[]) => {
      const result = await acknowledgeAlerts(targets.map((item) => item.id));
      const done = new Set(result.acknowledged);
      if (done.size > 0) {
        updateBell(withoutAlerts(done));
        onItemsRemoved();
      }
      if (result.failed.length > 0) {
        const titles = new Map(alerts.items.map((item) => [item.id, item.title]));
        const remaining = result.failed
          .map((item) => `${titles.get(item.alert_id) ?? 'An alert'} (${item.message})`)
          .join('; ');
        setNotice({
          alertId: null,
          tone: 'error',
          text: `${String(result.failed.length)} not acknowledged and still listed: ${remaining}`,
        });
      } else {
        setNotice({
          alertId: null,
          tone: 'info',
          text:
            done.size === 1 ? 'Alert acknowledged.' : `${String(done.size)} alerts acknowledged.`,
        });
      }
      void refresh();
    },
    [alerts.items, onItemsRemoved, refresh, updateBell],
  );

  const acknowledge = useCallback(
    (alert: BellAlert) => {
      void track([alert.id], async () => {
        try {
          await send([alert]);
        } catch (error) {
          setNotice({
            alertId: alert.id,
            tone: 'error',
            text: `Not acknowledged. ${describeError(error)} Try again.`,
          });
        }
      });
    },
    [send, track],
  );

  const shownAction = useCallback(
    async (targets: BellAlert[]) => {
      // A whole-request failure throws, so the confirmation stays open with a retry.
      await track(
        targets.map((item) => item.id),
        () => send(targets),
      );
    },
    [send, track],
  );
  const acknowledgeShown = useConfirmedAction(shownAction);

  const open = useCallback(
    (alert: BellAlert) => {
      void track([alert.id], async () => {
        try {
          const destination = await fetchAlertDestination(alert.id);
          const href = destinationHref(destination);
          if (href === null) {
            setNotice({ alertId: alert.id, tone: 'info', text: destination.message ?? GONE });
            return;
          }
          close();
          void navigate(href);
        } catch (error) {
          const gone = isApiError(error) && error.status === 404;
          setNotice({
            alertId: alert.id,
            tone: gone ? 'info' : 'error',
            text: gone ? GONE : `Could not open this alert. ${describeError(error)}`,
          });
          if (gone) void refresh();
        }
      });
    },
    [close, navigate, refresh, track],
  );

  const mute = useCallback(
    (alert: BellAlert) => {
      const ruleId = alert.indicator_id;
      if (ruleId === null) return;
      void track([alert.id], async () => {
        try {
          const preferences = await muteRule(ruleId);
          updateBell((bell) => ({ ...bell, preferences }));
          const name = preferences.muted_rules.find((rule) => rule.indicator_id === ruleId)?.name;
          setNotice({
            alertId: null,
            tone: 'info',
            text: `Alerts from ${name ?? 'this rule'} no longer appear in your bell. The rule still runs and other people still see them.`,
            undoRule: { id: ruleId, name: name ?? 'this rule' },
          });
          onItemsRemoved();
          await refresh();
        } catch (error) {
          setNotice({ alertId: alert.id, tone: 'error', text: describeError(error) });
        }
      });
    },
    [onItemsRemoved, refresh, track, updateBell],
  );

  const undoMute = useCallback(
    (ruleId: string) => {
      void track([`rule:${ruleId}`], async () => {
        try {
          const preferences = await unmuteRule(ruleId);
          updateBell((bell) => ({ ...bell, preferences }));
          setNotice({ alertId: null, tone: 'info', text: 'Rule unmuted.' });
          await refresh();
        } catch (error) {
          setNotice({ alertId: null, tone: 'error', text: describeError(error) });
        }
      });
    },
    [refresh, track, updateBell],
  );

  const dismissNotice = useCallback(() => setNotice(null), []);
  return { pending, notice, dismissNotice, open, acknowledge, mute, undoMute, acknowledgeShown };
}
