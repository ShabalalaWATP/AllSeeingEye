import { useState } from 'react';

import { CountryMultiSelect } from '@/components/research/CountryMultiSelect';
import { SelectField, TextField } from '@/components/ui/Field';
import type { LocationMode } from '@/lib/alertRules';
import { MAX_COUNTRIES } from '@/lib/alertRules';
import type { Country } from '@/lib/api/geoSchemas';
import { validateAreaBounds } from '@/lib/map/areaGeometry';
import type { MapBounds } from '@/lib/map/MapEngine';

const COORDINATES = ['west', 'south', 'east', 'north'] as const;

/** Rectangle bounds being edited, and the exact shape a hand-off or saved rule carries. */
export function useIndicatorArea(
  initialBounds: Readonly<MapBounds> | null,
  geometry: Record<string, unknown> | undefined,
  active: boolean,
) {
  const [fields, setFields] = useState(
    () =>
      Object.fromEntries(
        COORDINATES.map((key) => [key, initialBounds ? String(initialBounds[key]) : '']),
      ) as Record<keyof MapBounds, string>,
  );
  let bbox: [number, number, number, number] | undefined;
  let error: string | null = null;
  if (active)
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
  return { fields, setFields, bbox, error, geometry };
}

export function IndicatorAreaFields({
  mode,
  onModeChange,
  value,
  countries,
  onCountriesChange,
  catalogue,
  countriesError,
}: {
  mode: LocationMode;
  onModeChange: (mode: LocationMode) => void;
  value: ReturnType<typeof useIndicatorArea>;
  countries: string[];
  onCountriesChange: (value: string[]) => void;
  /** The country catalogue, or null while it is unavailable. */
  catalogue: readonly Country[] | null;
  countriesError: string | undefined;
}) {
  return (
    <fieldset className="space-y-3 rounded border border-line bg-ground/40 p-3">
      <legend className="px-1 text-sm font-medium">Watch location</legend>
      <SelectField
        label="Location scope"
        value={mode}
        onChange={(event) => onModeChange(event.target.value as LocationMode)}
        options={[
          { value: 'countries', label: 'Specific countries' },
          { value: 'worldwide', label: 'Worldwide (no location restriction)' },
          { value: 'area', label: 'Map area (rectangle)' },
          ...(value.geometry ? [{ value: 'shape', label: 'Exact drawn shape' }] : []),
        ]}
      />
      {mode === 'shape' ? (
        <p className="text-xs text-muted">
          The exact research boundary is retained, including holes. Only precisely located
          observations count. Switching to rectangle explicitly uses its enclosing bounds. Alerts
          only; use an area research subscription for reports.
        </p>
      ) : mode === 'worldwide' ? (
        <p className="text-xs text-muted">
          Items from anywhere count, including items with no recorded country. Choose specific
          countries or a map area to narrow the rule.
        </p>
      ) : mode === 'countries' ? (
        <CountryMultiSelect
          label="Countries to watch"
          countries={catalogue ?? []}
          value={countries}
          onChange={onCountriesChange}
          max={MAX_COUNTRIES}
          allowWorldwide={false}
          hint={`Choose up to ${String(MAX_COUNTRIES)}. Items filed under one of these countries count.`}
          error={countriesError}
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
