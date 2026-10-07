/**
 * Interactive monthly running-cost estimate for a self-hosted deployment. The
 * arithmetic lives in content/costing.ts; this component only holds the inputs.
 * While the cost model is a draft, the estimate says so plainly.
 */
import { useId, useMemo, useState } from 'react';

import { clampTo, estimate, formatRange, LIMITS } from '../content/costing';
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

function numberFrom(value: string, fallback: number): number {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function CostEstimator() {
  const id = useId();
  const [analysts, setAnalysts] = useState(10);
  const [runs, setRuns] = useState(3);
  const [depthId, setDepthId] = useState<string>('deep');
  const [presetId, setPresetId] = useState<string>('standard');
  const [hostingId, setHostingId] = useState<string>('standard');
  const [currency, setCurrency] = useState<Currency>('GBP');
  const preset = pick(PRICE_PRESETS, presetId);
  const [inputPrice, setInputPrice] = useState(preset.input);
  const [outputPrice, setOutputPrice] = useState(preset.output);

  const result = useMemo(
    () =>
      estimate({
        analysts,
        runsPerAnalystPerDay: runs,
        depth: pick(DEPTH_TOKENS, depthId),
        inputPrice,
        outputPrice,
        upliftPercent: DEFAULT_UPLIFT_PERCENT,
        hosting: pick(HOSTING_SIZES, hostingId),
        currency,
      }),
    [analysts, runs, depthId, inputPrice, outputPrice, hostingId, currency],
  );

  const choosePreset = (next: string) => {
    const chosen = PRICE_PRESETS.find((entry) => entry.id === next);
    setPresetId(next);
    if (chosen !== undefined) {
      setInputPrice(chosen.input);
      setOutputPrice(chosen.output);
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
          value={analysts}
          onChange={(event) =>
            setAnalysts(
              clampTo(
                Math.round(numberFrom(event.target.value, 1)),
                LIMITS.analysts.min,
                LIMITS.analysts.max,
              ),
            )
          }
        />
        <label htmlFor={`${id}-runs`}>Research runs per analyst per day</label>
        <input
          id={`${id}-runs`}
          type="number"
          inputMode="decimal"
          step={0.5}
          min={LIMITS.runs.min}
          max={LIMITS.runs.max}
          value={runs}
          onChange={(event) =>
            setRuns(clampTo(numberFrom(event.target.value, 0), LIMITS.runs.min, LIMITS.runs.max))
          }
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
          value={inputPrice}
          onChange={(event) =>
            setInputPrice(
              clampTo(numberFrom(event.target.value, 0), LIMITS.price.min, LIMITS.price.max),
            )
          }
        />
        <label htmlFor={`${id}-out`}>Output price, US$ per million tokens</label>
        <input
          id={`${id}-out`}
          type="number"
          inputMode="decimal"
          step={0.1}
          min={LIMITS.price.min}
          max={LIMITS.price.max}
          value={outputPrice}
          onChange={(event) =>
            setOutputPrice(
              clampTo(numberFrom(event.target.value, 0), LIMITS.price.min, LIMITS.price.max),
            )
          }
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
