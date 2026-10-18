/**
 * Constants behind the self-hosting cost estimator. Every figure carries its own
 * source and the date it was last checked, and the estimator's assumptions list is
 * generated from them. While `COST_MODEL_STATUS` is 'draft' the estimator says so on
 * screen and stays out of production builds: the token figures still need replacing
 * with measured medians from the AI usage ledger, and the hosting, price and exchange
 * figures need Alex's approval (KAN-178). Nothing here is a quote.
 */

export type CostModelStatus = 'draft' | 'approved';
export const COST_MODEL_STATUS: CostModelStatus = 'draft';

/** Where a figure came from and when it was last checked (ISO date, YYYY-MM-DD). */
export interface Sourced {
  source: string;
  checkedOn: string;
}

/** A single sourced number with the wording the assumptions list uses for it. */
export interface SourcedFigure extends Sourced {
  label: string;
  value: number;
}

export type Currency = 'GBP' | 'USD' | 'EUR';
export const CURRENCIES: readonly Currency[] = ['GBP', 'USD', 'EUR'];
export const CURRENCY_SYMBOLS: Record<Currency, string> = { GBP: '£', USD: 'US$', EUR: '€' };

const DRAFT_RATE =
  'Draft display rate, to be replaced with a dated published reference rate before launch';

/**
 * Model providers bill in US dollars and hosting is priced in sterling. Fixed, dated
 * rates convert both for display; each is the number of pounds one unit buys.
 */
export const EXCHANGE_RATES: Record<'USD' | 'EUR', SourcedFigure> = {
  USD: { label: 'US$1 in pounds', value: 0.75, source: DRAFT_RATE, checkedOn: '2026-10-07' },
  EUR: { label: '€1 in pounds', value: 0.85, source: DRAFT_RATE, checkedOn: '2026-10-18' },
};

export interface HostingSize extends Sourced {
  id: string;
  label: string;
  spec: string;
  analysts: string;
  /** Monthly server cost range in whole pounds. */
  low: number;
  high: number;
}

const DRAFT_HOSTING =
  'Draft indicative range, pending a named public provider price list and a check ' +
  'against the production footprint and ASE_LIVE_STORE_MEMORY_MB';

export const HOSTING_SIZES: readonly [HostingSize, HostingSize, HostingSize] = [
  {
    id: 'small',
    label: 'Small',
    spec: '4 vCPU · 8 GB RAM · 160 GB disk',
    analysts: 'Up to about 10 analysts',
    low: 15,
    high: 35,
    source: DRAFT_HOSTING,
    checkedOn: '2026-10-07',
  },
  {
    id: 'standard',
    label: 'Standard',
    spec: '8 vCPU · 16 GB RAM · 240 GB disk',
    analysts: 'About 10 to 50 analysts',
    low: 30,
    high: 70,
    source: DRAFT_HOSTING,
    checkedOn: '2026-10-07',
  },
  {
    id: 'large',
    label: 'Large',
    spec: '16 vCPU · 32 GB RAM, managed PostgreSQL',
    analysts: 'More than 50 analysts',
    low: 120,
    high: 260,
    source: DRAFT_HOSTING,
    checkedOn: '2026-10-07',
  },
];

export interface DepthTokens extends Sourced {
  id: 'basic' | 'deep' | 'advanced';
  label: string;
  /** Thousands of tokens per research run, as a low to high range. */
  inputLow: number;
  inputHigh: number;
  outputLow: number;
  outputHigh: number;
  /** Research runs behind the measured figures; null while the figures are a draft. */
  sampleSize: number | null;
  /** Date the ledger aggregate was exported; null while the figures are a draft. */
  sampledOn: string | null;
}

const DRAFT_TOKENS =
  'Draft placeholder, to be replaced with measured ai_usage_totals medians for this depth';

export const DEPTH_TOKENS: readonly [DepthTokens, DepthTokens, DepthTokens] = [
  {
    id: 'basic',
    label: 'Basic',
    inputLow: 120,
    inputHigh: 260,
    outputLow: 15,
    outputHigh: 35,
    source: DRAFT_TOKENS,
    checkedOn: '2026-10-07',
    sampleSize: null,
    sampledOn: null,
  },
  {
    id: 'deep',
    label: 'Deep',
    inputLow: 300,
    inputHigh: 650,
    outputLow: 40,
    outputHigh: 90,
    source: DRAFT_TOKENS,
    checkedOn: '2026-10-07',
    sampleSize: null,
    sampledOn: null,
  },
  {
    id: 'advanced',
    label: 'Advanced',
    inputLow: 650,
    inputHigh: 1400,
    outputLow: 90,
    outputHigh: 200,
    source: DRAFT_TOKENS,
    checkedOn: '2026-10-07',
    sampleSize: null,
    sampledOn: null,
  },
];

export interface PricePreset extends Sourced {
  id: string;
  label: string;
  /** US dollars per million tokens. */
  input: number;
  output: number;
}

const DRAFT_PRICE =
  'Draft illustrative price point, not a named model; to be replaced with dated ' +
  'provider list prices. Enter your own provider prices';

export const PRICE_PRESETS: readonly [PricePreset, PricePreset, PricePreset] = [
  {
    id: 'economy',
    label: 'Economy model',
    input: 0.4,
    output: 1.6,
    source: DRAFT_PRICE,
    checkedOn: '2026-10-07',
  },
  {
    id: 'standard',
    label: 'Standard model',
    input: 2.5,
    output: 10,
    source: DRAFT_PRICE,
    checkedOn: '2026-10-07',
  },
  {
    id: 'frontier',
    label: 'Frontier model',
    input: 15,
    output: 75,
    source: DRAFT_PRICE,
    checkedOn: '2026-10-07',
  },
];

export const WORKING_DAYS: SourcedFigure = {
  label: 'Working days a month',
  value: 21,
  source: 'Draft planning convention (about 252 working days a year), to be approved',
  checkedOn: '2026-10-07',
};

/** Assistant, briefings and subscriptions on top of manual research runs. */
export const DEFAULT_UPLIFT: SourcedFigure = {
  label: 'Default extra for the assistant, briefings and subscriptions (percent)',
  value: 25,
  source: 'Draft placeholder, to be replaced with measured ai_usage_totals shares',
  checkedOn: '2026-10-07',
};

/** The option with `id`, or the list's middle entry (every list has three). */
export function pick<T extends { id: string }>(items: readonly [T, T, T], id: string): T {
  return items.find((item) => item.id === id) ?? items[1];
}
