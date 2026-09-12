import { useId } from 'react';

import type { ReportRequest } from '@/lib/api/reports';

export const RESEARCH_DEPTHS = [
  {
    value: 'quick',
    label: 'Basic',
    length: '500–900 words',
    description: 'A concise answer with the key evidence and gaps.',
  },
  {
    value: 'detailed',
    label: 'Deep',
    length: '1,200–2,000 words',
    description: 'Broader collection, fuller analysis and a challenge to the findings.',
  },
  {
    value: 'advanced',
    label: 'Advanced',
    length: '2,500–4,000 words',
    description: 'Extended collection and synthesis, with more room for competing explanations.',
  },
] as const;

/** One set of report choices across one-off, area and scheduled research. */
export function ResearchDepth({
  value,
  onChange,
  disabled = false,
}: {
  value: NonNullable<ReportRequest['research_mode']>;
  onChange: (mode: NonNullable<ReportRequest['research_mode']>) => void;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <fieldset
      disabled={disabled}
      aria-describedby={`${id}-hint`}
      className="border-b border-line pb-5"
    >
      <legend className="mb-3 text-sm font-medium">Report type</legend>
      <div className="grid gap-2 sm:grid-cols-3">
        {RESEARCH_DEPTHS.map((option) => (
          <label
            key={option.value}
            className={`flex cursor-pointer items-start gap-3 rounded-md border p-4 transition-colors motion-reduce:transition-none ${value === option.value ? 'border-ember bg-surface-2' : 'border-line hover:bg-surface'}`}
          >
            <input
              type="radio"
              name={id}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
              className="mt-1 h-4 w-4 shrink-0 accent-ember"
            />
            <span className="text-sm font-medium">
              {option.label}
              <span className="mt-1 block text-xs text-ember">{option.length}</span>
              <span className="mt-2 block text-xs font-normal leading-relaxed text-muted">
                {option.description}
              </span>
            </span>
          </label>
        ))}
      </div>
      <p id={`${id}-hint`} className="mt-3 text-xs leading-relaxed text-muted">
        Lengths are indicative. Reports stay shorter when evidence is limited. Deeper research takes
        longer and uses more provider capacity.
      </p>
    </fieldset>
  );
}
