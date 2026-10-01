import { useCallback, useState } from 'react';

import { fetchEconomy, fetchEconomyNews } from '@/lib/api/economy';
import type { EconomyDays } from '@/lib/api/economyBriefing';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useVisiblePolling, type PollOutcome } from '@/lib/hooks/useVisiblePolling';

export const ECONOMY_REFRESH_MS = 300_000;

/**
 * Indicators and news for the economy page. Background refresh pauses in a hidden tab and
 * catches up at once when the tab returns after the interval has passed.
 */
export function useEconomyFeeds(days: EconomyDays) {
  const data = useScopedResource(fetchEconomy);
  const loadNews = useCallback(() => fetchEconomyNews(days), [days]);
  const news = useScopedResource(loadNews);
  const currentNews = news.data?.window_hours === days * 24 ? news.data : null;
  const [refreshing, setRefreshing] = useState(false);

  const refreshData = data.refresh;
  const refreshNews = news.refresh;
  const poll = useCallback(async (): Promise<PollOutcome> => {
    await Promise.all([refreshData(), refreshNews()]);
    return 'ok';
  }, [refreshData, refreshNews]);
  const { markLoaded } = useVisiblePolling({
    enabled: true,
    intervalMs: ECONOMY_REFRESH_MS,
    poll,
  });

  const reloadData = data.reload;
  const reloadNews = news.reload;
  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await Promise.all([reloadData(), reloadNews()]);
      markLoaded();
    } finally {
      setRefreshing(false);
    }
  }, [markLoaded, reloadData, reloadNews]);

  return { data, news, currentNews, refreshing, refresh };
}
