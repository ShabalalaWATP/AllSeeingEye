import { useId, useState } from 'react';
import type { ChangeEvent, KeyboardEvent } from 'react';

import type { Country } from '@/lib/api/geoSchemas';

export interface NationFilterProps {
  countries: readonly Country[];
  /** ISO 3166-1 alpha-2 of the selected nation, or null for the whole world. */
  value: string | null;
  onChange: (iso: string | null) => void;
  /** Why the country list could not be loaded, if it could not. */
  error?: string | null;
}

/** Finds a nation by exact name, ISO code, or (on Enter) the first name that starts with the text. */
export function matchCountry(
  countries: readonly Country[],
  text: string,
  allowPrefix: boolean,
): Country | null {
  const needle = text.trim().toLowerCase();
  if (needle === '') return null;
  const exact = countries.find(
    (country) => country.name.toLowerCase() === needle || country.iso2.toLowerCase() === needle,
  );
  if (exact !== undefined || !allowPrefix) return exact ?? null;
  return countries.find((country) => country.name.toLowerCase().startsWith(needle)) ?? null;
}

/** A nation picker over the whole list; typing a full name or code selects it, Enter completes. */
export function NationFilter({ countries, value, onChange, error = null }: NationFilterProps) {
  const listId = useId();
  const selected = value === null ? null : (countries.find((c) => c.iso2 === value) ?? null);
  const [text, setText] = useState('');
  const shown = selected === null ? text : selected.name;

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const next = event.target.value;
    setText(next);
    const match = matchCountry(countries, next, false);
    if (match !== null) onChange(match.iso2);
    else if (selected !== null) onChange(null);
  };

  const handleKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== 'Enter') return;
    const match = matchCountry(countries, text, true);
    if (match !== null) {
      setText(match.name);
      onChange(match.iso2);
    }
  };

  const clear = () => {
    setText('');
    onChange(null);
  };

  return (
    <div className="rounded-md border border-line bg-surface/90 p-1.5 backdrop-blur">
      <div className="flex items-center gap-1">
        <input
          type="text"
          role="combobox"
          aria-label="Nation filter"
          aria-expanded="false"
          aria-controls={listId}
          list={listId}
          placeholder="Nation"
          autoComplete="off"
          value={shown}
          onChange={handleChange}
          onKeyDown={handleKey}
          className="min-w-0 flex-1 bg-transparent px-1.5 py-1 text-sm text-text placeholder:text-muted focus:outline-none"
        />
        <datalist id={listId}>
          {countries.map((country) => (
            <option key={country.iso2} value={country.name} />
          ))}
        </datalist>
        {selected !== null && (
          <button
            type="button"
            aria-label="Clear nation filter"
            onClick={clear}
            className="rounded px-1.5 text-muted hover:bg-surface-2 hover:text-text"
          >
            ×
          </button>
        )}
      </div>
      {error !== null && (
        <p role="alert" className="mt-1 px-1.5 text-xs text-critical">
          Nations unavailable: {error}
        </p>
      )}
    </div>
  );
}
