/**
 * Constants behind the self-hosting cost estimator. Every figure carries its source
 * and the date it was checked. While `COST_MODEL_STATUS` is 'draft' the estimator
 * says so on screen: the token figures still need replacing with measured medians
 * from the AI usage ledger, and the hosting and price points need Alex's approval
 * (KAN-178). Nothing here is a quote.
 */

export type CostModelStatus = 'draft' | 'approved';
export const COST_MODEL_STATUS: CostModelStatus = 'draft';
export const COST_MODEL_CHECKED_ON = '2026-10-07';

export type Currency = 'GBP' | 'USD';
/** Model providers bill in US dollars; one fixed, dated rate converts for display. */
export const USD_TO_GBP = 0.75;

export interface HostingSize {
  id: string;
  label: string;
  spec: string;
  analysts: string;
  /** Monthly server cost range in GBP. */
  low: number;
  high: number;
}

export const HOSTING_SIZES: readonly [HostingSize, HostingSize, HostingSize] = [
  {
    id: 'small',
    label: 'Small',
    spec: '4 vCPU · 8 GB RAM · 160 GB disk',
    analysts: 'Up to about 10 analysts',
    low: 15,
    high: 35,
  },
  {
    id: 'standard',
    label: 'Standard',
    spec: '8 vCPU · 16 GB RAM · 240 GB disk',
    analysts: 'About 10 to 50 analysts',
    low: 30,
    high: 70,
  },
  {
    id: 'large',
    label: 'Large',
    spec: '16 vCPU · 32 GB RAM, managed PostgreSQL',
    analysts: 'More than 50 analysts',
    low: 120,
    high: 260,
  },
];

export interface DepthTokens {
  id: 'basic' | 'deep' | 'advanced';
  label: string;
  /** Thousands of tokens per research run, as a low to high range. */
  inputLow: number;
  inputHigh: number;
  outputLow: number;
  outputHigh: number;
}

/** Draft: replace with measured medians and spreads from ai_usage_totals per depth. */
export const DEPTH_TOKENS: readonly [DepthTokens, DepthTokens, DepthTokens] = [
  { id: 'basic', label: 'Basic', inputLow: 120, inputHigh: 260, outputLow: 15, outputHigh: 35 },
  { id: 'deep', label: 'Deep', inputLow: 300, inputHigh: 650, outputLow: 40, outputHigh: 90 },
  {
    id: 'advanced',
    label: 'Advanced',
    inputLow: 650,
    inputHigh: 1400,
    outputLow: 90,
    outputHigh: 200,
  },
];

export interface PricePreset {
  id: string;
  label: string;
  /** US dollars per million tokens. */
  input: number;
  output: number;
}

/** Illustrative price points only; the reader is asked to enter their provider's prices. */
export const PRICE_PRESETS: readonly [PricePreset, PricePreset, PricePreset] = [
  { id: 'economy', label: 'Economy model', input: 0.4, output: 1.6 },
  { id: 'standard', label: 'Standard model', input: 2.5, output: 10 },
  { id: 'frontier', label: 'Frontier model', input: 15, output: 75 },
];

export const WORKING_DAYS_PER_MONTH = 21;
/** Assistant, briefings and subscriptions on top of manual research runs. */
export const DEFAULT_UPLIFT_PERCENT = 25;

/** The option with `id`, or the list's middle entry (every list has three). */
export function pick<T extends { id: string }>(items: readonly [T, T, T], id: string): T {
  return items.find((item) => item.id === id) ?? items[1];
}
