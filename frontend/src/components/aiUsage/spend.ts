/** Present estimated spend beside recorded tokens. Never presented as a bill. */
import type { AiTokenPrices, AiUsageTotals } from '@/lib/api/aiUsage';

/** The wording used everywhere a figure is shown, so nobody reads it as an invoice. */
export const SPEND_CAVEAT = 'Estimated from recorded tokens at the configured prices, not a bill.';

/**
 * A formatted amount, or null when no price is configured and money must stay hidden.
 * The backend rounds the estimate; this only formats what it sent.
 */
export function formatSpend(amount: string | null | undefined, prices: AiTokenPrices): string | null {
  if (!prices.configured || amount === null || amount === undefined) return null;
  const value = Number(amount);
  if (!Number.isFinite(value)) return null;
  // Four decimal places below a cent, so a single mechanical call is not shown as zero.
  const digits = value !== 0 && Math.abs(value) < 0.01 ? 4 : 2;
  return `${prices.currency} ${value.toFixed(digits)}`;
}

export function spendOf(totals: AiUsageTotals, prices: AiTokenPrices): string | null {
  return formatSpend(totals.estimated_cost, prices);
}
