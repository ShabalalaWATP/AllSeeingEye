/**
 * Pure arithmetic for the cost estimator. Amounts are worked in whole pennies or
 * cents and rounded once, so ranges never drift through floating-point sums. The
 * assumptions list, the staleness check and the enquiry summary are generated here
 * from the dated figures in costModel.ts.
 */
import {
  COST_MODEL_STATUS,
  CURRENCY_SYMBOLS,
  DEFAULT_UPLIFT,
  DEPTH_TOKENS,
  EXCHANGE_RATES,
  HOSTING_SIZES,
  PRICE_PRESETS,
  WORKING_DAYS,
  type CostModelStatus,
  type Currency,
  type DepthTokens,
  type HostingSize,
  type PricePreset,
  type Sourced,
  type SourcedFigure,
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
  /** Minor units: pennies for GBP, cents for USD and EUR. */
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

function clampTo(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

/** The input with every figure brought within its limits. */
export function normaliseInput(raw: EstimateInput): EstimateInput {
  return {
    ...raw,
    analysts: Math.round(clampTo(raw.analysts, LIMITS.analysts.min, LIMITS.analysts.max)),
    runsPerAnalystPerDay: clampTo(raw.runsPerAnalystPerDay, LIMITS.runs.min, LIMITS.runs.max),
    inputPrice: clampTo(raw.inputPrice, LIMITS.price.min, LIMITS.price.max),
    outputPrice: clampTo(raw.outputPrice, LIMITS.price.min, LIMITS.price.max),
    upliftPercent: clampTo(raw.upliftPercent, LIMITS.uplift.min, LIMITS.uplift.max),
  };
}

function aiUsdCents(runs: number, inputK: number, outputK: number, input: EstimateInput): number {
  const perRun = (inputK * 1000 * input.inputPrice + outputK * 1000 * input.outputPrice) / 1e6;
  return Math.round(runs * perRun * (1 + input.upliftPercent / 100) * 100);
}

/** US cents into the display currency's minor units, rounded once. */
export function fromUsdCents(cents: number, currency: Currency): number {
  if (currency === 'USD') return cents;
  const pence = cents * EXCHANGE_RATES.USD.value;
  return Math.round(currency === 'GBP' ? pence : pence / EXCHANGE_RATES.EUR.value);
}

/** Whole pounds into the display currency's minor units, rounded once. */
export function fromGbpPounds(pounds: number, currency: Currency): number {
  const pence = pounds * 100;
  if (currency === 'GBP') return pence;
  return Math.round(pence / EXCHANGE_RATES[currency].value);
}

export function estimate(raw: EstimateInput): Estimate {
  const input = normaliseInput(raw);
  const runsPerMonth = Math.round(input.analysts * input.runsPerAnalystPerDay * WORKING_DAYS.value);
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

/** An estimate is shown in whole units of the currency, never to the penny. */
export function wholeUnits(minor: number): number {
  return Math.round(minor / 100);
}

export function formatMoney(minor: number, currency: Currency): string {
  return `${CURRENCY_SYMBOLS[currency]}${wholeUnits(minor).toLocaleString('en-GB')}`;
}

export function formatRange(range: Range, currency: Currency): string {
  if (wholeUnits(range.low) === wholeUnits(range.high)) return formatMoney(range.low, currency);
  return `${formatMoney(range.low, currency)} to ${formatMoney(range.high, currency)}`;
}

export interface FigureRule {
  min: number;
  max: number;
  /** Shown at the start of an error message, for example 'Analysts'. */
  noun: string;
  integer?: boolean;
  /** Used when the field is left blank; without one a blank field is an error. */
  fallback?: number;
}

export type FigureCheck = { ok: true; value: number } | { ok: false; message: string };

/** Reads one typed figure. Nothing is clamped silently: a bad figure gets a message. */
export function validateFigure(text: string, rule: FigureRule): FigureCheck {
  const trimmed = text.trim();
  if (trimmed === '' && rule.fallback !== undefined) return { ok: true, value: rule.fallback };
  const kind = rule.integer === true ? 'a whole number' : 'a number';
  const range = `from ${rule.min.toLocaleString('en-GB')} to ${rule.max.toLocaleString('en-GB')}`;
  if (trimmed === '')
    return { ok: false, message: `${rule.noun} is required: enter ${kind} ${range}.` };
  const value = Number(trimmed);
  const whole = rule.integer !== true || Number.isInteger(value);
  if (!Number.isFinite(value) || !whole || value < rule.min || value > rule.max) {
    return { ok: false, message: `${rule.noun} must be ${kind} ${range}.` };
  }
  return { ok: true, value };
}

export const STALE_AFTER_DAYS = 90;
const DAY_MS = 86_400_000;

/**
 * True when `checkedOn` (YYYY-MM-DD) is more than `maxAgeDays` calendar days before
 * the visitor's `today`. An unreadable date counts as stale, so it is never hidden.
 */
export function isStale(checkedOn: string, today: Date, maxAgeDays = STALE_AFTER_DAYS): boolean {
  const checked = Date.parse(`${checkedOn}T00:00:00Z`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(checkedOn) || Number.isNaN(checked)) return true;
  const day = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  return (day - checked) / DAY_MS > maxAgeDays;
}

/** A checked date for display, for example '7 October 2026'; unreadable dates as given. */
export function formatCheckedOn(checkedOn: string): string {
  const time = Date.parse(`${checkedOn}T00:00:00Z`);
  if (Number.isNaN(time)) return checkedOn;
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(time);
}

export interface CostModel {
  hosting: readonly HostingSize[];
  depths: readonly DepthTokens[];
  prices: readonly PricePreset[];
  workingDays: SourcedFigure;
  uplift: SourcedFigure;
  rates: Record<'USD' | 'EUR', SourcedFigure>;
}

export const COST_MODEL: CostModel = {
  hosting: HOSTING_SIZES,
  depths: DEPTH_TOKENS,
  prices: PRICE_PRESETS,
  workingDays: WORKING_DAYS,
  uplift: DEFAULT_UPLIFT,
  rates: EXCHANGE_RATES,
};

export interface Assumption extends Sourced {
  id: string;
  label: string;
  value: string;
}

function usd(price: number): string {
  return `US$${price.toFixed(2)}`;
}

/** How the token figures for a depth were measured, or that they have not been yet. */
export function describeSample(depth: DepthTokens): string {
  if (depth.sampleSize === null || depth.sampledOn === null) return 'not yet measured';
  return `${depth.sampleSize.toLocaleString('en-GB')} runs, exported ${depth.sampledOn}`;
}

/** Every constant behind the estimate, with its source and checked date. */
export function listAssumptions(model: CostModel = COST_MODEL): Assumption[] {
  return [
    ...model.hosting.map((size) => ({
      id: `hosting-${size.id}`,
      label: `${size.label} server (${size.spec})`,
      value: `£${size.low} to £${size.high} a month`,
      source: size.source,
      checkedOn: size.checkedOn,
    })),
    ...model.depths.map((depth) => ({
      id: `tokens-${depth.id}`,
      label: `${depth.label} research run`,
      value:
        `${depth.inputLow}k to ${depth.inputHigh}k input and ${depth.outputLow}k to ` +
        `${depth.outputHigh}k output tokens; sample: ${describeSample(depth)}`,
      source: depth.source,
      checkedOn: depth.checkedOn,
    })),
    ...model.prices.map((preset) => ({
      id: `price-${preset.id}`,
      label: `${preset.label} price point`,
      value: `${usd(preset.input)} input and ${usd(preset.output)} output per million tokens`,
      source: preset.source,
      checkedOn: preset.checkedOn,
    })),
    {
      id: 'working-days',
      label: model.workingDays.label,
      value: `${model.workingDays.value}`,
      source: model.workingDays.source,
      checkedOn: model.workingDays.checkedOn,
    },
    {
      id: 'uplift',
      label: model.uplift.label,
      value: `${model.uplift.value} percent`,
      source: model.uplift.source,
      checkedOn: model.uplift.checkedOn,
    },
    ...(['USD', 'EUR'] as const).map((code) => ({
      id: `rate-${code}`,
      label: model.rates[code].label,
      value: `£${model.rates[code].value.toFixed(2)}`,
      source: model.rates[code].source,
      checkedOn: model.rates[code].checkedOn,
    })),
  ];
}

/** The figures older than the review window, so the page can say they are under review. */
export function staleAssumptions(today: Date, model: CostModel = COST_MODEL): Assumption[] {
  return listAssumptions(model).filter((entry) => isStale(entry.checkedOn, today));
}

export const SUMMARY_LIMIT = 2000;

/**
 * A plain-text summary for the enquiry message, at most SUMMARY_LIMIT characters. It
 * says it is an estimate and, while the model is a draft, that the figures are drafts.
 */
export function summariseEstimate(
  raw: EstimateInput,
  priceLabel: string,
  status: CostModelStatus = COST_MODEL_STATUS,
): string {
  const input = normaliseInput(raw);
  const result = estimate(input);
  const money = (range: Range) => formatRange(range, input.currency);
  const lines = [
    'Self-hosting running-cost estimate from the product page. This is an estimate, not a quote.',
    ...(status === 'draft' ? ['The figures are drafts and have not yet been reviewed.'] : []),
    '',
    `Analysts: ${input.analysts}`,
    `Research runs per analyst per day: ${input.runsPerAnalystPerDay}`,
    `Typical depth: ${input.depth.label}`,
    `Model prices: ${priceLabel}, ${usd(input.inputPrice)} input and ${usd(input.outputPrice)} output per million tokens`,
    `Extra for the assistant, briefings and subscriptions: ${input.upliftPercent} percent`,
    `Server size: ${input.hosting.label} (${input.hosting.spec})`,
    '',
    `Estimated monthly running cost in ${input.currency}:`,
    `AI usage (${result.runsPerMonth.toLocaleString('en-GB')} runs a month): ${money(result.ai)}`,
    `Server: ${money(result.hosting)}`,
    'Licence and support: quoted on enquiry',
    `Total: ${money(result.total)}`,
  ];
  return lines.join('\n').slice(0, SUMMARY_LIMIT);
}
