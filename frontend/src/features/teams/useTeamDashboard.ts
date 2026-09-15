import { useCallback, useEffect, useState } from 'react';

import { asApiError, describeError } from '@/lib/api/errors';
import { getTeamDashboard, type TeamDashboard } from '@/lib/api/teamBoard';

/** Loads the bounded team overview; access is decided by the server on every request. */
export function useTeamDashboard(teamId: string) {
  const [data, setData] = useState<TeamDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getTeamDashboard(teamId));
    } catch (caught) {
      setData(null);
      setError(describeError(asApiError(caught)));
    } finally {
      setLoading(false);
    }
  }, [teamId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  return { data, error, loading, reload: load };
}
