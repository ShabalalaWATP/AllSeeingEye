/**
 * Interactive monthly running-cost estimate for a self-hosted deployment. The
 * arithmetic lives in content/costing.ts and the state in useCostEstimator; this
 * component only lays out the inputs. While the cost model is a draft, or any figure
 * is older than the review window, the estimate says so plainly.
 */
import { useId } from 'react';

import { LIMITS, STALE_AFTER_DAYS } from '../content/costing';
import {
  COST_MODEL_STATUS,
  CURRENCIES,
  DEFAULT_UPLIFT,
  DEPTH_TOKENS,
  HOSTING_SIZES,
  PRICE_PRESETS,
} from '../content/costModel';
import { EstimatorAssumptions } from './EstimatorAssumptions';
import { EstimatorField } from './EstimatorField';
import { EstimatorResult } from './EstimatorResult';
import { useCostEstimator } from './useCostEstimator';

export function CostEstimator() {
  const id = useId();
  const estimator = useCostEstimator();
  const { fields, choices } = estimator;

  return (
    <div className="estimator">
      {COST_MODEL_STATUS === 'draft' ? (
        <p className="estimator-draft" role="note">
          Draft figures, not yet reviewed. Token use per run will be replaced with measured figures
          before this estimator is published.
        </p>
      ) : null}
      {estimator.stale.length > 0 ? (
        <p className="estimator-draft" role="note">
          Figures under review: {estimator.stale.length} of the figures behind this estimate were
          last checked more than {STALE_AFTER_DAYS} days ago.
        </p>
      ) : null}
      <form className="estimator-form" noValidate onSubmit={(event) => event.preventDefault()}>
        <EstimatorField
          id={`${id}-analysts`}
          label="Analysts"
          field={fields.analysts}
          {...LIMITS.analysts}
          integer
        />
        <EstimatorField
          id={`${id}-runs`}
          label="Research runs per analyst per day"
          field={fields.runs}
          {...LIMITS.runs}
          step={0.5}
        />
        <label htmlFor={`${id}-depth`}>Typical depth</label>
        <select
          id={`${id}-depth`}
          value={choices.depthId}
          onChange={(event) => estimator.setDepthId(event.target.value)}
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
          value={choices.presetId}
          onChange={(event) => estimator.choosePreset(event.target.value)}
        >
          {PRICE_PRESETS.map((entry) => (
            <option key={entry.id} value={entry.id}>
              {entry.label}
            </option>
          ))}
        </select>
        <EstimatorField
          id={`${id}-in`}
          label="Input price, US$ per million tokens"
          field={fields.inputPrice}
          {...LIMITS.price}
          step={0.1}
        />
        <EstimatorField
          id={`${id}-out`}
          label="Output price, US$ per million tokens"
          field={fields.outputPrice}
          {...LIMITS.price}
          step={0.1}
        />
        <EstimatorField
          id={`${id}-uplift`}
          label="Extra for the assistant, briefings and subscriptions, percent (optional)"
          field={fields.uplift}
          {...LIMITS.uplift}
          hint={`Leave blank for the default of ${DEFAULT_UPLIFT.value} percent.`}
        />
        <label htmlFor={`${id}-hosting`}>Server size</label>
        <select
          id={`${id}-hosting`}
          value={choices.hostingId}
          onChange={(event) => estimator.setHostingId(event.target.value)}
        >
          {HOSTING_SIZES.map((entry) => (
            <option key={entry.id} value={entry.id}>{`${entry.label}: ${entry.spec}`}</option>
          ))}
        </select>
        <fieldset className="estimator-currency">
          <legend>Currency</legend>
          {CURRENCIES.map((code) => (
            <label key={code}>
              <input
                type="radio"
                name={`${id}-currency`}
                value={code}
                checked={choices.currency === code}
                onChange={() => estimator.setCurrency(code)}
              />
              {code}
            </label>
          ))}
        </fieldset>
      </form>
      <div className="estimator-result">
        <EstimatorResult
          result={estimator.result}
          currency={choices.currency}
          invalid={estimator.invalid}
          summary={estimator.summary}
        />
        <EstimatorAssumptions />
      </div>
    </div>
  );
}
