/**
 * State for the cost estimator: the typed figures with their messages, the chosen
 * options and the derived estimate. Inputs are never stored or sent anywhere.
 */
import { useState } from 'react';

import {
  estimate,
  LIMITS,
  staleAssumptions,
  summariseEstimate,
  validateFigure,
  type FigureRule,
} from '../content/costing';
import {
  DEFAULT_UPLIFT,
  DEPTH_TOKENS,
  HOSTING_SIZES,
  pick,
  PRICE_PRESETS,
  type Currency,
} from '../content/costModel';

export interface FigureField {
  /** Exactly what the reader has typed. */
  text: string;
  /** The last valid figure, which the estimate keeps using while the text is wrong. */
  value: number;
  /** Why the typed text is not used, or null when it is. */
  error: string | null;
  type: (text: string) => void;
  set: (value: number) => void;
}

function useFigure(initial: number, rule: FigureRule): FigureField {
  const [text, setText] = useState(String(initial));
  const [value, setValue] = useState(initial);
  const check = validateFigure(text, rule);
  return {
    text,
    value,
    error: check.ok ? null : check.message,
    type: (next) => {
      setText(next);
      const read = validateFigure(next, rule);
      if (read.ok) setValue(read.value);
    },
    set: (next) => {
      setText(String(next));
      setValue(next);
    },
  };
}

export function useCostEstimator() {
  const analysts = useFigure(10, { ...LIMITS.analysts, noun: 'Analysts', integer: true });
  const runs = useFigure(3, { ...LIMITS.runs, noun: 'Research runs per day' });
  const [depthId, setDepthId] = useState<string>('deep');
  const [presetId, setPresetId] = useState<string>('standard');
  const [hostingId, setHostingId] = useState<string>('standard');
  const [currency, setCurrency] = useState<Currency>('GBP');
  const preset = pick(PRICE_PRESETS, presetId);
  const inputPrice = useFigure(preset.input, { ...LIMITS.price, noun: 'Input price' });
  const outputPrice = useFigure(preset.output, { ...LIMITS.price, noun: 'Output price' });
  const uplift = useFigure(DEFAULT_UPLIFT.value, {
    ...LIMITS.uplift,
    noun: 'The extra percentage',
    fallback: DEFAULT_UPLIFT.value,
  });
  // Checked once per visit against the visitor's own date.
  const [stale] = useState(() => staleAssumptions(new Date()));

  const input = {
    analysts: analysts.value,
    runsPerAnalystPerDay: runs.value,
    depth: pick(DEPTH_TOKENS, depthId),
    inputPrice: inputPrice.value,
    outputPrice: outputPrice.value,
    upliftPercent: uplift.value,
    hosting: pick(HOSTING_SIZES, hostingId),
    currency,
  };
  const custom = input.inputPrice !== preset.input || input.outputPrice !== preset.output;
  const fields = [analysts, runs, inputPrice, outputPrice, uplift];

  const choosePreset = (next: string) => {
    const chosen = PRICE_PRESETS.find((entry) => entry.id === next);
    setPresetId(next);
    if (chosen !== undefined) {
      inputPrice.set(chosen.input);
      outputPrice.set(chosen.output);
    }
  };

  return {
    fields: { analysts, runs, inputPrice, outputPrice, uplift },
    choices: { depthId, presetId, hostingId, currency },
    setDepthId,
    choosePreset,
    setHostingId,
    setCurrency,
    result: estimate(input),
    invalid: fields.some((field) => field.error !== null),
    stale,
    summary: () => summariseEstimate(input, custom ? 'Custom prices' : preset.label),
  };
}
