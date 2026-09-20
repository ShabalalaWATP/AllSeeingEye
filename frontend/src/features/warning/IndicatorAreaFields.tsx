import { useState } from 'react';
import { SelectField, TextField } from '@/components/ui/Field';
import type { AreaWatchDraft } from '@/lib/areaWatchDraft';
import { validateAreaBounds } from '@/lib/map/areaGeometry';
import type { MapBounds } from '@/lib/map/MapEngine';

const COORDINATES = ['west', 'south', 'east', 'north'] as const;
export function useIndicatorArea(draft: AreaWatchDraft | null) {
  const [mode, setMode] = useState(draft?.geometry ? 'shape' : draft ? 'area' : 'nations');
  const [fields, setFields] = useState(
    () =>
      Object.fromEntries(
        COORDINATES.map((key) => [key, draft ? String(draft.bounds[key]) : '']),
      ) as Record<keyof MapBounds, string>,
  );
  let bbox: [number, number, number, number] | undefined;
  let error: string | null = null;
  if (mode === 'area')
    try {
      if (COORDINATES.some((key) => fields[key].trim() === ''))
        throw new Error('Enter all four bounds.');
      const bounds = validateAreaBounds(
        Object.fromEntries(
          COORDINATES.map((key) => [key, Number(fields[key])]),
        ) as unknown as MapBounds,
      );
      bbox = [bounds.west, bounds.south, bounds.east, bounds.north];
    } catch (failure) {
      error = failure instanceof Error ? failure.message : 'Enter valid bounds.';
    }
  const geometry = draft?.geometry;
  return { mode, setMode, fields, setFields, bbox, error, geometry };
}

export function IndicatorAreaFields({
  value,
  countries,
  onCountriesChange,
}: {
  value: ReturnType<typeof useIndicatorArea>;
  countries: string;
  onCountriesChange: (value: string) => void;
}) {
  return (
    <fieldset className="space-y-3 rounded border border-line bg-ground/40 p-3">
      <legend className="px-1 text-sm font-medium">Watch location</legend>
      <SelectField
        label="Location scope"
        value={value.mode}
        onChange={(event) => value.setMode(event.target.value)}
        options={[
          { value: 'nations', label: 'Nations or worldwide' },
          { value: 'area', label: 'Map area (rectangle)' },
          ...(value.geometry ? [{ value: 'shape', label: 'Exact drawn shape' }] : []),
        ]}
      />
      {value.mode === 'shape' ? (
        <p className="text-xs text-muted">
          The exact research boundary is retained, including holes. Only precisely located
          observations count. Switching to rectangle explicitly uses its enclosing bounds. Alerts
          only; use an area research subscription for reports.
        </p>
      ) : value.mode === 'nations' ? (
        <TextField
          label="Nations"
          hint="ISO codes, comma separated; blank watches everywhere."
          value={countries}
          onChange={(event) => onCountriesChange(event.target.value)}
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {COORDINATES.map((key) => (
              <TextField
                key={key}
                label={`${key.charAt(0).toUpperCase()}${key.slice(1)} bound`}
                type="number"
                step="any"
                required
                min={key === 'west' || key === 'east' ? -180 : -90}
                max={key === 'west' || key === 'east' ? 180 : 90}
                value={value.fields[key]}
                onChange={(event) =>
                  value.setFields({ ...value.fields, [key]: event.target.value })
                }
              />
            ))}
          </div>
          <p className="text-xs leading-relaxed text-muted">
            WGS84 longitude and latitude. West greater than east crosses the date line. Only items
            with a map point inside this rectangle count; reported locations may be approximate.
            This does not detect arrivals or departures.
          </p>
          {value.error && (
            <p role="alert" className="text-sm text-critical">
              {value.error}
            </p>
          )}
        </>
      )}
    </fieldset>
  );
}
