import { SelectField, TextField } from '@/components/ui/Field';
import { BASE_LAYER_OPTIONS } from '@/lib/map/baseLayers';
import type { MapState } from '@/lib/api/mapViews';

export function MapFilters({
  state,
  onChange,
  days,
  sources,
}: {
  state: MapState;
  onChange: (value: MapState) => void;
  days: string[];
  sources: [string, string][];
}) {
  const day = state.published_until?.slice(0, 10) ?? '';
  const sinceOnly = !!state.published_since && !state.published_until;
  const dates = [...new Set([...days, ...(day ? [day] : [])])].sort();
  const recorded = state.time_basis === 'recorded_time';
  const acquisition = state.time_basis === 'acquisition_or_publication';
  const dateKind = recorded
    ? 'project/observation/reporting'
    : acquisition
      ? 'observation/reporting'
      : 'publication';
  return (
    <div className="space-y-3">
      <SelectField
        label="Timeline time basis"
        value={state.time_basis}
        onChange={(event) =>
          onChange({
            ...state,
            time_basis:
              event.target.value === 'recorded_time'
                ? 'recorded_time'
                : event.target.value === 'acquisition_or_publication'
                  ? 'acquisition_or_publication'
                  : 'publication',
          })
        }
        options={[
          { value: 'publication', label: 'Publication dates' },
          { value: 'recorded_time', label: 'Project years, acquisition and publication' },
          {
            value: 'acquisition_or_publication',
            label: 'Acquisition dates where recorded, otherwise publication',
          },
        ]}
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField
          label={
            recorded
              ? 'Project / acquisition / publication timeline (UTC)'
              : acquisition
                ? 'Acquisition / publication timeline (UTC)'
                : 'Publication timeline (UTC)'
          }
          value={sinceOnly ? '__since_only__' : day}
          onChange={(event) => {
            if (event.target.value === '__since_only__') return;
            onChange({
              ...state,
              published_since: event.target.value ? state.published_since : null,
              published_until: event.target.value ? `${event.target.value}T23:59:59.999Z` : null,
              include_unknown_dates: !event.target.value,
            });
          }}
          options={[
            { value: '', label: `All ${dateKind} dates` },
            ...(sinceOnly
              ? [
                  {
                    value: '__since_only__',
                    label:
                      acquisition || recorded
                        ? 'Custom range: from a start date'
                        : 'Custom range: published from a start date',
                  },
                ]
              : []),
            ...dates.map((value) => ({
              value,
              label: `${recorded ? 'Recorded' : acquisition ? 'Acquired / published' : 'Published'} through ${value}`,
            })),
          ]}
        />
        <SelectField
          label="Evidence source"
          value={state.source_ids.length > 1 ? '__multiple__' : (state.source_ids[0] ?? '')}
          onChange={(event) => {
            if (event.target.value !== '__multiple__')
              onChange({ ...state, source_ids: event.target.value ? [event.target.value] : [] });
          }}
          options={[
            { value: '', label: 'All sources' },
            ...(state.source_ids.length > 1
              ? [{ value: '__multiple__', label: `${state.source_ids.length} selected sources` }]
              : []),
            ...sources.map(([value, label]) => ({ value, label })),
          ]}
        />
      </div>
      {(state.published_since ?? state.published_until) && !state.include_unknown_dates && (
        <p className="text-xs text-muted">
          Records without a valid {dateKind} date are excluded from this date filter. Choose All
          {` ${dateKind} dates`} to inspect them.
        </p>
      )}
      <details>
        <summary className="cursor-pointer text-sm">Additional map filters and basemap</summary>
        <div className="mt-3 space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            {(['published_since', 'published_until'] as const).map((field) => (
              <TextField
                key={field}
                type="datetime-local"
                step="1"
                label={
                  field === 'published_since'
                    ? acquisition || recorded
                      ? 'Time from (UTC)'
                      : 'Published from (UTC)'
                    : acquisition || recorded
                      ? 'Time until (UTC)'
                      : 'Published until (UTC)'
                }
                value={state[field] ? new Date(state[field]).toISOString().slice(0, 19) : ''}
                onChange={(event) =>
                  onChange({
                    ...state,
                    [field]: event.target.value ? `${event.target.value}Z` : null,
                  })
                }
              />
            ))}
          </div>
          <label className="flex gap-2 text-sm">
            <input
              type="checkbox"
              checked={state.include_unknown_dates}
              onChange={(event) =>
                onChange({ ...state, include_unknown_dates: event.target.checked })
              }
            />
            Include unknown {dateKind} dates
          </label>
          <fieldset>
            <legend className="text-sm">Source selection (none selected means all)</legend>
            {sources.map(([id, name]) => (
              <label key={id} className="mt-1 flex gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={state.source_ids.includes(id)}
                  onChange={(event) =>
                    onChange({
                      ...state,
                      source_ids: event.target.checked
                        ? [...state.source_ids, id]
                        : state.source_ids.filter((source) => source !== id),
                    })
                  }
                />
                {name}
              </label>
            ))}
          </fieldset>
          <SelectField
            label="Evidence basemap"
            value={state.basemap}
            onChange={(event) =>
              onChange({ ...state, basemap: event.target.value as MapState['basemap'] })
            }
            options={BASE_LAYER_OPTIONS.map((option) => ({
              value: option.id,
              label: `${option.label} (${option.coverage})`,
            }))}
          />
        </div>
      </details>
    </div>
  );
}
