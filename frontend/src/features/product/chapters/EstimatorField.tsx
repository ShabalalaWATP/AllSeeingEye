/**
 * One labelled number input for the cost estimator. A figure it cannot use is never
 * clamped silently: the message is shown beside the field, tied to it with
 * aria-describedby and announced politely as it changes.
 */
import type { FigureField } from './useCostEstimator';

export interface EstimatorFieldProps {
  id: string;
  label: string;
  field: FigureField;
  min: number;
  max: number;
  step?: number;
  integer?: boolean;
  hint?: string;
}

export function EstimatorField({
  id,
  label,
  field,
  min,
  max,
  step,
  integer = false,
  hint,
}: EstimatorFieldProps) {
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [
    hint === undefined ? null : hintId,
    field.error === null ? null : errorId,
  ].filter((entry) => entry !== null);
  return (
    <>
      <label htmlFor={id}>{label}</label>
      <div className="estimator-field">
        <input
          id={id}
          type="number"
          inputMode={integer ? 'numeric' : 'decimal'}
          min={min}
          max={max}
          step={step}
          value={field.text}
          aria-invalid={field.error === null ? undefined : true}
          aria-describedby={describedBy.length === 0 ? undefined : describedBy.join(' ')}
          onChange={(event) => field.type(event.target.value)}
        />
        {hint === undefined ? null : (
          <p id={hintId} className="estimator-hint">
            {hint}
          </p>
        )}
        <p id={errorId} className="estimator-error" aria-live="polite">
          {field.error ?? ''}
        </p>
      </div>
    </>
  );
}
