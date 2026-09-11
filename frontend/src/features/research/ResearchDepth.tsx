import type { ReportRequest } from '@/lib/api/reports';

export function ResearchDepth({
  value,
  onChange,
  disabled,
}: {
  value: NonNullable<ReportRequest['research_mode']>;
  onChange: (mode: NonNullable<ReportRequest['research_mode']>) => void;
  disabled: boolean;
}) {
  return (
    <fieldset
      disabled={disabled}
      className="grid gap-x-6 gap-y-2 border-b border-line pb-5 sm:grid-cols-2"
    >
      <legend className="mb-2 text-sm font-medium">Research depth</legend>
      {(
        [
          ['quick', 'Quick', 'A focused research run.'],
          ['detailed', 'Detailed', 'Broader research with a separate challenge to the judgements.'],
        ] as const
      ).map(([mode, label, description]) => (
        <label key={mode} className="flex min-h-16 cursor-pointer items-start gap-3 rounded py-3">
          <input
            type="radio"
            name="research-depth"
            value={mode}
            checked={value === mode}
            onChange={() => onChange(mode)}
            className="mt-1 h-4 w-4 shrink-0 accent-ember"
          />
          <span className="text-sm font-medium">
            {label}
            <span className="mt-1 block text-xs font-normal leading-relaxed text-muted">
              {description}
            </span>
          </span>
        </label>
      ))}
    </fieldset>
  );
}
