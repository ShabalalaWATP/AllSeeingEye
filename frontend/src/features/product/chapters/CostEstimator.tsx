/**
 * Interactive monthly running-cost estimate for a self-hosted deployment. The
 * arithmetic lives in content/costing.ts; this component only holds the inputs.
 * While the cost model is a draft, the estimate says so plainly.
 */
import { useId, useMemo, useState } from 'react';

import { useNumberField } from '@/lib/hooks/useNumberField';

import { estimate, formatRange, LIMITS } from '../content/costing';
import {
  COST_MODEL_CHECKED_ON,
  COST_MODEL_STATUS,
  DEFAULT_UPLIFT_PERCENT,
  DEPTH_TOKENS,
  HOSTING_SIZES,
  pick,
  PRICE_PRESETS,
  USD_TO_GBP,
  WORKING_DAYS_PER_MONTH,
  type Currency,
} from '../content/costModel';

export function CostEstimator() {
  const id = useId();
  // Each figure keeps its typed text, so a field can be cleared; it settles on blur.
  const analysts = useNumberField(10, { ...LIMITS.analysts, integer: true });
  const runs = useNumberField(3, LIMITS.runs);
  const [depthId, setDepthId] = useState<string>('deep');
  const [presetId, setPresetId] = useState<string>('standard');
  const [hostingId, setHostingId] = useState<string>('standard');
  const [currency, setCurrency] = useState<Currency>('GBP');
  const preset = pick(PRICE_PRESETS, presetId);
  const inputPrice = useNumberField(preset.input, LIMITS.price);
  const outputPrice = useNumberField(preset.output, LIMITS.price);

  const result = useMemo(
    () =>
      estimate({
        analysts: analysts.value,
        runsPerAnalystPerDay: runs.value,
        depth: pick(DEPTH_TOKENS, depthId),
        inputPrice: inputPrice.value,
        outputPrice: outputPrice.value,
        upliftPercent: DEFAULT_UPLIFT_PERCENT,
        hosting: pick(HOSTING_SIZES, hostingId),
        currency,
      }),
    [analysts.value, runs.value, depthId, inputPrice.value, outputPrice.value, hostingId, currency],
  );

  const choosePreset = (next: string) => {
    const chosen = PRICE_PRESETS.find((entry) => entry.id === next);
    setPresetId(next);
    if (chosen !== undefined) {
      inputPrice.set(chosen.input);
      outputPrice.set(chosen.output);
    }
  };

  return (
    <div className="estimator">
      {COST_MODEL_STATUS === 'draft' ? (
        <p className="estimator-draft" role="note">
          Draft figures, not yet reviewed. Token use per run will be replaced with measured figures
          before this estimator is published.
        </p>
      ) : null}
      <form className="estimator-form" onSubmit={(event) => event.preventDefault()}>
        <label htmlFor={`${id}-analysts`}>Analysts</label>
        <input
          id={`${id}-analysts`}
          type="number"
          inputMode="numeric"
          min={LIMITS.analysts.min}
          max={LIMITS.analysts.max}
          value={analysts.text}
          onChange={(event) => analysts.type(event.target.value)}
          onBlur={analysts.commit}
        />
        <label htmlFor={`${id}-runs`}>Research runs per analyst per day</label>
        <input
          id={`${id}-runs`}
          type="number"
          inputMode="decimal"
          step={0.5}
          min={LIMITS.runs.min}
          max={LIMITS.runs.max}
          value={runs.text}
          onChange={(event) => runs.type(event.target.value)}
          onBlur={runs.commit}
        />
        <label htmlFor={`${id}-depth`}>Typical depth</label>
        <select
          id={`${id}-depth`}
          value={depthId}
          onChange={(event) => setDepthId(event.target.value)}
        >
          {DEPTH_TOKENS.map((entry) => (
            <option key={entry.id} value={entry.id}>
              {entry.label}
            </option>
          ))}
        </select>
        <label htmlFor={`${id}-model`}>Model price point</label>
        <select
          id={`${id}-model`}
          value={presetId}
          onChange={(event) => choosePreset(event.target.value)}
        >
          {PRICE_PRESETS.map((entry) => (
            <option key={entry.id} value={entry.id}>
              {entry.label}
            </option>
          ))}
        </select>
        <label htmlFor={`${id}-in`}>Input price, US$ per million tokens</label>
        <input
          id={`${id}-in`}
          type="number"
          inputMode="decimal"
          step={0.1}
          min={LIMITS.price.min}
          max={LIMITS.price.max}
          value={inputPrice.text}
          onChange={(event) => inputPrice.type(event.target.value)}
          onBlur={inputPrice.commit}
        />
        <label htmlFor={`${id}-out`}>Output price, US$ per million tokens</label>
        <input
          id={`${id}-out`}
          type="number"
          inputMode="decimal"
          step={0.1}
          min={LIMITS.price.min}
          max={LIMITS.price.max}
          value={outputPrice.text}
          onChange={(event) => outputPrice.type(event.target.value)}
          onBlur={outputPrice.commit}
        />
        <label htmlFor={`${id}-hosting`}>Server size</label>
        <select
          id={`${id}-hosting`}
          value={hostingId}
          onChange={(event) => setHostingId(event.target.value)}
        >
          {HOSTING_SIZES.map((entry) => (
            <option key={entry.id} value={entry.id}>{`${entry.label}: ${entry.spec}`}</option>
          ))}
        </select>
        <fieldset className="estimator-currency">
          <legend>Currency</legend>
          {(['GBP', 'USD'] as const).map((code) => (
            <label key={code}>
              <input
                type="radio"
                name={`${id}-currency`}
                value={code}
                checked={currency === code}
                onChange={() => setCurrency(code)}
              />
              {code}
            </label>
          ))}
        </fieldset>
      </form>
      <div className="estimator-result" aria-live="polite">
        <p className="estimator-total">
          <span>Estimated monthly running cost</span>
          <strong>{formatRange(result.total, currency)}</strong>
        </p>
        <dl>
          <dt>AI usage ({result.runsPerMonth.toLocaleString('en-GB')} runs a month)</dt>
          <dd>{formatRange(result.ai, currency)}</dd>
          <dt>Server</dt>
          <dd>{formatRange(result.hosting, currency)}</dd>
          <dt>Licence and support</dt>
          <dd>Quoted on enquiry</dd>
        </dl>
        <details className="estimator-assumptions">
          <summary>Assumptions</summary>
          <ul>
            <li>{WORKING_DAYS_PER_MONTH} working days a month.</li>
            <li>
              {DEFAULT_UPLIFT_PERCENT} percent added for the assistant, briefings and subscriptions.
            </li>
            <li>Model prices are illustrative; enter your provider&rsquo;s own prices.</li>
            <li>US$1 = £{USD_TO_GBP.toFixed(2)}, fixed for display.</li>
            <li>Figures checked on {COST_MODEL_CHECKED_ON}. An estimate, not a quote.</li>
          </ul>
        </details>
      </div>
    </div>
  );
}
