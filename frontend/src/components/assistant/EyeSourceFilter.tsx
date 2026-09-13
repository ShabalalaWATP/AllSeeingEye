import type { Category } from '@/lib/api/eventSchemas';

export type EyeSourceCategory = Category | 'camera' | 'infrastructure' | 'doctrine';

const SOURCE_TYPES: readonly { id: EyeSourceCategory; label: string }[] = [
  { id: 'news', label: 'News' },
  { id: 'conflict', label: 'Conflicts' },
  { id: 'disaster', label: 'Natural hazards' },
  { id: 'aviation', label: 'Flights' },
  { id: 'maritime', label: 'Ships' },
  { id: 'space', label: 'Space' },
  { id: 'cyber', label: 'Cyber' },
  { id: 'social', label: 'Social' },
  { id: 'political', label: 'Politics' },
  { id: 'humanitarian', label: 'Humanitarian' },
  { id: 'economic', label: 'Economy' },
  { id: 'camera', label: 'CCTV' },
  { id: 'infrastructure', label: 'Infrastructure' },
  { id: 'doctrine', label: 'UK/NATO doctrine' },
];

/** Explicit source restriction is optional; an empty selection restores automatic routing. */
export function EyeSourceFilter({
  value,
  onChange,
  disabled,
}: {
  value: EyeSourceCategory[] | null;
  onChange: (value: EyeSourceCategory[] | null) => void;
  disabled: boolean;
}) {
  return (
    <details className="eye-source-filter">
      <summary>
        Source types <span>{value?.length ? `${value.length} selected` : 'Automatic'}</span>
      </summary>
      <div>
        <p>Automatic uses sources relevant to your question. Choose types to narrow the search.</p>
        {value && (
          <button type="button" onClick={() => onChange(null)} disabled={disabled}>
            Use automatic selection
          </button>
        )}
        <div className="eye-source-choices" role="group" aria-label="Source types to search">
          {SOURCE_TYPES.map(({ id, label }) => (
            <label key={id}>
              <input
                type="checkbox"
                checked={value?.includes(id) ?? false}
                disabled={disabled}
                onChange={(event) => {
                  const next = event.target.checked
                    ? [...(value ?? []), id]
                    : (value ?? []).filter((item) => item !== id);
                  onChange(next.length ? next : null);
                }}
              />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </div>
    </details>
  );
}
