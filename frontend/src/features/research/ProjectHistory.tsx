import { SelectField, TextField } from '@/components/ui/Field';

export interface ProjectHistoryState {
  enabled: boolean;
  firstYear: string;
  lastYear: string;
}

export function projectInterval(history: ProjectHistoryState) {
  const first = Number(history.firstYear);
  const last = Number(history.lastYear);
  if (
    !/^\d{4}$/.test(history.firstYear) ||
    !/^\d{4}$/.test(history.lastYear) ||
    first < 1000 ||
    last > 9998 ||
    last < first ||
    last - first >= 30
  )
    return null;
  return {
    since: `${first}-01-01T00:00:00.000Z`,
    until: `${last + 1}-01-01T00:00:00.000Z`,
  };
}

export function ProjectHistory({
  value,
  onChange,
}: {
  value: ProjectHistoryState;
  onChange: (value: ProjectHistoryState) => void;
}) {
  return (
    <div className="grid gap-4">
      <SelectField
        label="Research period"
        value={value.enabled ? 'history' : 'recent'}
        options={[
          { value: 'recent', label: 'Recent reporting' },
          { value: 'history', label: 'Historical project commitments' },
        ]}
        onChange={(event) => onChange({ ...value, enabled: event.target.value === 'history' })}
      />
      {value.enabled && (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField
              label="First commitment year"
              inputMode="numeric"
              maxLength={4}
              value={value.firstYear}
              onChange={(event) => onChange({ ...value, firstYear: event.target.value })}
            />
            <TextField
              label="Last commitment year"
              inputMode="numeric"
              maxLength={4}
              value={value.lastYear}
              onChange={(event) => onChange({ ...value, lastYear: event.target.value })}
            />
          </div>
          <p className="text-xs text-muted">
            Both years are included, up to 30 years. Select a project source and preview before
            starting. Country means project recipient. Commitments are not payments or evidence of
            current activity. Source coverage may be narrower than your chosen period.
          </p>
        </>
      )}
    </div>
  );
}
