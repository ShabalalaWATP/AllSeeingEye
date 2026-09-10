import { RF_FIELDS } from '@/lib/map/rfPlanning';
import type { RfInputs } from '@/lib/map/rfPlanning';
import type { RfDraft, RfPropagation } from '@/lib/map/rfDraft';
import { RfEngineeringControls } from './RfEngineeringControls';

const BASIC_FIELDS = new Set<keyof RfInputs>([
  'frequencyMHz',
  'transmitHeightM',
  'receiveHeightM',
  'distanceKm',
]);
const SHORT_LABELS: Partial<Record<keyof RfInputs, string>> = {
  transmitHeightM: 'TX antenna height (m AGL)',
  receiveHeightM: 'RX antenna height (m AGL)',
};

export function RfRadioFields({
  draft,
  mode,
  input,
  linked,
  onChange,
  onDraftChange,
}: {
  draft: RfDraft;
  mode: RfPropagation;
  input: RfInputs;
  linked: boolean;
  onChange: (key: keyof RfInputs, value: string) => void;
  onDraftChange: (draft: RfDraft) => void;
}) {
  const field = ({ key, label, min, max }: (typeof RF_FIELDS)[number]) => (
    <label key={key} className="rf-field">
      <span>{SHORT_LABELS[key] ?? label}</span>
      <input
        aria-label={label}
        type="number"
        min={min}
        max={max}
        step="any"
        value={key === 'distanceKm' && linked ? input.distanceKm.toFixed(3) : draft.values[key]}
        readOnly={key === 'distanceKm' && linked}
        onChange={(event) => onChange(key, event.target.value)}
      />
    </label>
  );
  return (
    <>
      <div className="rf-field-grid">
        {RF_FIELDS.filter(({ key }) => key === 'frequencyMHz').map(field)}
        {mode !== 'hf-skywave' &&
          RF_FIELDS.filter(
            ({ key }) =>
              BASIC_FIELDS.has(key) &&
              key !== 'frequencyMHz' &&
              (key !== 'distanceKm' || mode === 'free-space' || (mode === 'terrain' && linked)),
          ).map(field)}
      </div>
      {mode !== 'hf-skywave' && (
        <>
          <p className="rf-help">
            Antenna heights are above local ground. Terrain analysis adds ground elevation
            separately.
          </p>
          <details className="rf-disclosure">
            <summary>Link budget &amp; engineering settings</summary>
            <div className="rf-disclosure-body">
              <div className="rf-field-grid">
                {RF_FIELDS.filter(({ key }) => !BASIC_FIELDS.has(key)).map(field)}
              </div>
              <RfEngineeringControls draft={draft} onChange={onDraftChange} />
            </div>
          </details>
        </>
      )}
    </>
  );
}
