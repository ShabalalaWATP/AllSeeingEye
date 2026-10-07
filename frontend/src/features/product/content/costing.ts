/**
 * Pure arithmetic for the cost estimator. Amounts are worked in whole pennies or
 * cents and rounded once, so ranges never drift through floating-point sums.
 */
import {
  USD_TO_GBP,
  WORKING_DAYS_PER_MONTH,
  type Currency,
  type DepthTokens,
  type HostingSize,
} from './costModel';

export interface EstimateInput {
  analysts: number;
  runsPerAnalystPerDay: number;
  depth: DepthTokens;
  /** US dollars per million tokens. */
  inputPrice: number;
  outputPrice: number;
  upliftPercent: number;
  hosting: HostingSize;
  currency: Currency;
}

export interface Range {
  /** Minor units: pennies for GBP, cents for USD. */
  low: number;
  high: number;
}

export interface Estimate {
  runsPerMonth: number;
  ai: Range;
  hosting: Range;
  total: Range;
}

export const LIMITS = {
  analysts: { min: 1, max: 500 },
  runs: { min: 0, max: 40 },
  price: { min: 0, max: 1000 },
  uplift: { min: 0, max: 200 },
} as const;

export function clampTo(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

function aiUsdCents(runs: number, inputK: number, outputK: number, input: EstimateInput): number {
  const perRun = (inputK * 1000 * input.inputPrice + outputK * 1000 * input.outputPrice) / 1e6;
  return Math.round(runs * perRun * (1 + input.upliftPercent / 100) * 100);
}

function fromUsdCents(cents: number, currency: Currency): number {
  return currency === 'USD' ? cents : Math.round(cents * USD_TO_GBP);
}

function fromGbpPounds(pounds: number, currency: Currency): number {
  return currency === 'GBP' ? pounds * 100 : Math.round((pounds / USD_TO_GBP) * 100);
}

export function estimate(raw: EstimateInput): Estimate {
  const input: EstimateInput = {
    ...raw,
    analysts: Math.round(clampTo(raw.analysts, LIMITS.analysts.min, LIMITS.analysts.max)),
    runsPerAnalystPerDay: clampTo(raw.runsPerAnalystPerDay, LIMITS.runs.min, LIMITS.runs.max),
    inputPrice: clampTo(raw.inputPrice, LIMITS.price.min, LIMITS.price.max),
    outputPrice: clampTo(raw.outputPrice, LIMITS.price.min, LIMITS.price.max),
    upliftPercent: clampTo(raw.upliftPercent, LIMITS.uplift.min, LIMITS.uplift.max),
  };
  const runsPerMonth = Math.round(
    input.analysts * input.runsPerAnalystPerDay * WORKING_DAYS_PER_MONTH,
  );
  const { depth } = input;
  const ai = {
    low: fromUsdCents(
      aiUsdCents(runsPerMonth, depth.inputLow, depth.outputLow, input),
      input.currency,
    ),
    high: fromUsdCents(
      aiUsdCents(runsPerMonth, depth.inputHigh, depth.outputHigh, input),
      input.currency,
    ),
  };
  const hosting = {
    low: fromGbpPounds(input.hosting.low, input.currency),
    high: fromGbpPounds(input.hosting.high, input.currency),
  };
  return {
    runsPerMonth,
    ai,
    hosting,
    total: { low: ai.low + hosting.low, high: ai.high + hosting.high },
  };
}

export function formatMoney(minor: number, currency: Currency): string {
  const major = minor / 100;
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
    maximumFractionDigits: major >= 100 ? 0 : 2,
  }).format(major);
}

export function formatRange(range: Range, currency: Currency): string {
  if (range.low === range.high) return formatMoney(range.low, currency);
  return `${formatMoney(range.low, currency)} to ${formatMoney(range.high, currency)}`;
}
