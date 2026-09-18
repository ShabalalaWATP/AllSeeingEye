/**
 * A bounded multiple choice as a row of toggles, for the few-from-a-few decisions a
 * form asks (which regions, which themes). Each chip is a real checkbox, so keyboard
 * and assistive users get a labelled group with a stated limit, not a styled div.
 */
import { useId } from 'react';

export interface ChipOption<T extends string> {
  readonly value: T;
  readonly label: string;
  readonly hint?: string;
}

export function ChipPicker<T extends string>({
  label,
  hint,
  options,
  value,
  onChange,
  max,
  disabled = false,
}: {
  label: string;
  hint?: string;
  options: readonly ChipOption<T>[];
  value: readonly T[];
  onChange: (value: T[]) => void;
  max: number;
  disabled?: boolean;
}) {
  const hintId = useId();
  const full = value.length >= max;
  return (
    <fieldset disabled={disabled} className="min-w-0 space-y-3" aria-describedby={hintId}>
      {/* The count is hidden from the name so the group reads as its label alone. */}
      <legend className="flex w-full items-baseline justify-between gap-3 text-sm font-medium">
        <span>{label}</span>
        <span aria-hidden="true" className="font-mono text-[11px] text-muted">
          {value.length} / {max}
        </span>
      </legend>
      <p id={hintId} className="text-xs text-muted">
        {hint && <span>{hint} </span>}
        <span className="sr-only">
          {value.length} of {max} chosen.
        </span>
      </p>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const selected = value.includes(option.value);
          return (
            <label
              key={option.value}
              title={option.hint}
              className={`inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-full border px-4 text-sm transition-colors motion-reduce:transition-none has-disabled:cursor-not-allowed has-disabled:opacity-50 ${
                selected
                  ? 'border-ember bg-ember/15 text-text'
                  : 'border-line bg-ground text-muted hover:border-ember/40 hover:text-text'
              }`}
            >
              <input
                type="checkbox"
                className="sr-only"
                checked={selected}
                disabled={!selected && full}
                onChange={(event) =>
                  onChange(
                    event.target.checked
                      ? [...value, option.value]
                      : value.filter((item) => item !== option.value),
                  )
                }
              />
              <span aria-hidden="true" className={selected ? 'text-ember' : 'text-line'}>
                {selected ? '●' : '○'}
              </span>
              {option.label}
            </label>
          );
        })}
      </div>
      {full && (
        <p role="status" className="text-xs text-muted">
          {max} chosen. Remove one to add another.
        </p>
      )}
    </fieldset>
  );
}
