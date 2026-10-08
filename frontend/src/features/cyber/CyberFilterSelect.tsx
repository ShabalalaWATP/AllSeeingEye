export const CYBER_FIELD =
  'min-h-11 rounded-md border border-control-border bg-surface px-3 text-sm text-text focus:border-ember';

/** One labelled reporting filter with an "all" choice first. */
export function CyberFilterSelect<T extends string>({
  label,
  value,
  onChange,
  allLabel,
  options,
}: {
  label: string;
  value: T | '';
  onChange: (value: T | '') => void;
  allLabel: string;
  options: readonly (readonly [T, string])[];
}) {
  return (
    <label className="flex flex-col gap-2 text-xs text-muted">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as T | '')}
        className={CYBER_FIELD}
      >
        <option value="">{allLabel}</option>
        {options.map(([key, text]) => (
          <option key={key} value={key}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
}
