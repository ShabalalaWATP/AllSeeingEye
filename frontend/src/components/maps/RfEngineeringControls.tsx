import type { RfDraft } from '@/lib/map/rfDraft';
import { RF_ENGINEERING_DRAFT_DEFAULTS, RF_ENGINEERING_FIELDS } from '@/lib/map/rfEngineering';

export function RfEngineeringControls({
  draft,
  onChange,
}: {
  draft: RfDraft;
  onChange: (draft: RfDraft) => void;
}) {
  const mode = draft.propagation ?? 'terrain';
  if (mode === 'hf-skywave') return null;
  const values = { ...RF_ENGINEERING_DRAFT_DEFAULTS, ...draft.engineering };
  return (
    <fieldset className="rf-engineering-controls">
      <legend className="rf-section-label">Planning assumptions</legend>
      <div className="rf-field-grid">
        {RF_ENGINEERING_FIELDS.filter(
          ({ key }) =>
            key === 'reserveDb' ||
            mode === 'terrain' ||
            (key === 'earthFactor' && mode === 'free-space'),
        ).map(({ key, label, min, max, step }) => (
          <label className="rf-field" key={key}>
            <span>{label}</span>
            <input
              type="number"
              aria-label={label}
              value={values[key]}
              min={min}
              max={max}
              step={key === 'earthFactor' ? 'any' : step}
              onChange={(event) =>
                onChange({ ...draft, engineering: { ...values, [key]: event.target.value } })
              }
            />
          </label>
        ))}
      </div>
      <p className="rf-help">
        Reserve is the spare margin required above receiver sensitivity. The default 10 dB is a
        planning allowance, not a reliability guarantee. Use the radio’s sensitivity for the
        required bandwidth and data rate.
      </p>
      {mode === 'terrain' && (
        <p className="rf-help">
          Obstacle height adds a uniform assumed screen between the sites. It does not detect
          buildings or trees, or model their material losses. Mast heights remain above local
          ground.
        </p>
      )}
      {(mode === 'terrain' || mode === 'free-space') && (
        <p className="rf-help">
          k = 1.333 assumes standard refraction. A smaller value gives a more restrictive horizon.
          This is a manual scenario, not live weather.
        </p>
      )}
    </fieldset>
  );
}
