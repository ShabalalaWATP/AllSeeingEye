import { useCallback, useEffect, useState } from 'react';

import { asApiError, describeError } from '@/lib/api/errors';
import { getTeamDashboard, type TeamDashboard } from '@/lib/api/teamBoard';
import { useVisiblePolling, type PollOutcome } from '@/lib/hooks/useVisiblePolling';

import { isTeamAccessLoss as isAccessLoss } from './teamCapabilities';

export const DASHBOARD_REFRESH_INTERVAL = 60_000;

/** Loads the bounded team overview; access is decided by the server on every request. */
export function useTeamDashboard(teamId: string) {
  const [data, setData] = useState<TeamDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [accessLost, setAccessLost] = useState(false);
  const [refreshFailed, setRefreshFailed] = useState(false);

  const refresh = useCallback(
    async (signal: AbortSignal): Promise<PollOutcome> => {
      try {
        // A manual reload disables polling, which aborts this request before it can land.
        const next = await getTeamDashboard(teamId, signal);
        setData(next);
        setError(null);
        setRefreshFailed(false);
        return 'ok';
      } catch (caught) {
        if (signal.aborted) return 'skipped';
        if (!isAccessLoss(asApiError(caught).status)) {
          setRefreshFailed(true);
          return 'failed';
        }
        setData(null);
        setRefreshFailed(false);
        setAccessLost(true);
        return 'stop';
      }
    },
    [teamId],
  );
  const { markLoaded } = useVisiblePolling({
    enabled: !accessLost && !loading,
    intervalMs: DASHBOARD_REFRESH_INTERVAL,
    poll: refresh,
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setRefreshFailed(false);
    try {
      setData(await getTeamDashboard(teamId));
      setAccessLost(false);
    } catch (caught) {
      setData(null);
      const failure = asApiError(caught);
      setAccessLost(isAccessLoss(failure.status));
      if (!isAccessLoss(failure.status)) setError(describeError(failure));
    } finally {
      markLoaded();
      setLoading(false);
    }
  }, [markLoaded, teamId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  return { data, error, loading, accessLost, refreshFailed, reload: load };
}
