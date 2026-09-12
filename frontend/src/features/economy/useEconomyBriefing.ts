import { useCallback } from 'react';
import { ensureEconomyBriefing, type EconomyDays } from '@/lib/api/economyBriefing';
import { useBriefing } from '@/lib/hooks/useDailyBriefing';

export function useEconomyBriefing(days: EconomyDays) {
  const ensure = useCallback((signal: AbortSignal) => ensureEconomyBriefing(days, signal), [days]);
  return useBriefing(ensure);
}
export type EconomyBriefingState = ReturnType<typeof useEconomyBriefing>;
