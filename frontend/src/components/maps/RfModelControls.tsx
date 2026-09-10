import { RF_ENVIRONMENT_DEFAULTS } from '@/lib/map/rfDraft';
import type { RfDraft, RfEnvironment, RfPropagation } from '@/lib/map/rfDraft';
const MODES: { id: RfPropagation; label: string; description: string }[] = [
  {
    id: 'terrain',
    label: 'Terrain-aware VHF / UHF',
    description:
      '30 MHz and above. Samples ground elevations for terrain obstruction and clearance; not measured radio coverage.',
  },
  {
    id: 'free-space',
    label: 'Free-space reference',
    description:
      'Ideal link budget and smooth-Earth horizon only. Ignores terrain, buildings and ionospheric propagation.',
  },
  {
    id: 'hf-groundwave',
    label: 'HF groundwave',
    description:
      '1.6 to 30 MHz. Native NTIA LFMF model over a homogeneous ground surface. Enter assumed electrical ground properties.',
  },
  {
    id: 'hf-skywave',
    label: 'HF skywave scenario',
    description:
      '1.6 to 30 MHz. User-defined single-hop geometry, not an ionospheric forecast or received-signal prediction.',
  },
];
interface Field {
  key: keyof RfEnvironment;
  label: string;
  min: number;
  max: number;
}
function fields(mode: RfPropagation): Field[] {
  if (mode === 'terrain')
    return [{ key: 'radiusKm', label: 'Sampling radius (km)', min: 1, max: 50 }];
  if (mode === 'hf-groundwave')
    return [
      { key: 'radiusKm', label: 'Maximum groundwave distance (km)', min: 2, max: 200 },
      { key: 'conductivitySm', label: 'Ground conductivity (S/m)', min: 0.00001, max: 10 },
      { key: 'permittivity', label: 'Relative permittivity', min: 1, max: 100 },
      { key: 'refractivity', label: 'Surface refractivity (N-units)', min: 250, max: 400 },
    ];
  if (mode === 'hf-skywave')
    return [
      { key: 'criticalFrequencyMHz', label: 'Assumed foF2 (MHz)', min: 0.5, max: 20 },
      { key: 'virtualHeightKm', label: 'Virtual layer height (km)', min: 80, max: 600 },
      { key: 'minElevationDeg', label: 'Minimum launch elevation (degrees)', min: 0, max: 90 },
      { key: 'maxElevationDeg', label: 'Maximum launch elevation (degrees)', min: 0, max: 90 },
    ];
  return [];
}
export function rfEnvironmentValid(draft: RfDraft) {
  const env = { ...RF_ENVIRONMENT_DEFAULTS, ...draft.environment };
  const mode = draft.propagation ?? 'terrain';
  return (
    fields(mode).every(
      ({ key, min, max }) =>
        env[key].trim() !== '' &&
        Number.isFinite(Number(env[key])) &&
        Number(env[key]) >= min &&
        Number(env[key]) <= max,
    ) &&
    (mode !== 'hf-skywave' || Number(env.minElevationDeg) <= Number(env.maxElevationDeg))
  );
}
export function RfModelControls({
  draft,
  onChange,
}: {
  draft: RfDraft;
  onChange: (draft: RfDraft) => void;
}) {
  const mode = draft.propagation ?? 'terrain';
  const env = { ...RF_ENVIRONMENT_DEFAULTS, ...draft.environment };
  const change = (key: keyof RfEnvironment, value: string) =>
    onChange({ ...draft, environment: { ...env, [key]: value } });
  return (
    <div className="rf-model">
      <label className="rf-field">
        Propagation model
        <select
          value={mode}
          onChange={(event) =>
            onChange({ ...draft, propagation: event.target.value as RfPropagation })
          }
        >
          {MODES.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <p className="rf-help">{MODES.find((item) => item.id === mode)?.description}</p>
      {mode === 'hf-groundwave' && (
        <label className="rf-field">
          Ground conductivity shortcut
          <select
            value={
              ['0.001', '0.005', '0.03', '5'].includes(env.conductivitySm)
                ? env.conductivitySm
                : 'custom'
            }
            onChange={(event) => {
              if (event.target.value !== 'custom') change('conductivitySm', event.target.value);
            }}
          >
            <option value="custom">Custom assumption</option>
            <option value="0.001">Poor ground / 0.001 S/m</option>
            <option value="0.005">Average ground / 0.005 S/m</option>
            <option value="0.03">Conductive ground / 0.03 S/m</option>
            <option value="5">Sea water / 5 S/m</option>
          </select>
        </label>
      )}
      {mode === 'hf-groundwave' && (
        <p className="rf-help">
          These shortcuts change conductivity only. Relative permittivity is unchanged; enter an
          appropriate separate assumption.
        </p>
      )}
      <div className="rf-field-grid">
        {fields(mode).map(({ key, label, min, max }) => (
          <label key={key} className="rf-field">
            {label}
            <input
              type="number"
              min={min}
              max={max}
              step="any"
              value={env[key]}
              onChange={(event) => change(key, event.target.value)}
            />
          </label>
        ))}
      </div>
    </div>
  );
}
