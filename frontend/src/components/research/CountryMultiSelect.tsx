import { useId, useState } from 'react';
import { TextField } from '@/components/ui/Field';
import type { Country } from '@/lib/api/geoSchemas';

export const MAX_RESEARCH_COUNTRIES = 8;

/** A small, searchable checklist keeps country selection usable with the full catalogue. */
export function CountryMultiSelect({
  countries,
  value: selected,
  onChange,
  disabled = false,
  label: title = 'Countries',
}: {
  countries: readonly Country[];
  value: string[];
  onChange: (countries: string[]) => void;
  disabled?: boolean;
  label?: string;
}) {
  const [search, setSearch] = useState('');
  const hintId = useId();
  const query = search.trim().toLocaleLowerCase();
  const matches = countries.filter((country) =>
    `${country.name} ${country.iso2}`.toLocaleLowerCase().includes(query),
  );
  const label = (code: string) =>
    countries.find((country) => country.iso2 === code)?.name ?? `Unavailable country: ${code}`;
  return (
    <fieldset disabled={disabled} className="min-w-0 space-y-3" aria-describedby={hintId}>
      <legend className="text-sm font-medium">{title}</legend>
      <p id={hintId} className="text-xs text-muted">
        Choose up to eight. Leave empty for worldwide research.
      </p>
      <div className="flex min-h-9 flex-wrap items-center gap-2" aria-label="Selected countries">
        {selected.length === 0 ? (
          <span className="text-sm text-text">Worldwide</span>
        ) : (
          selected.map((code) => (
            <button
              type="button"
              key={code}
              aria-label={`Remove ${label(code)}`}
              onClick={() => onChange(selected.filter((value) => value !== code))}
              className="flex min-h-9 items-center gap-2 rounded-md border border-ember/35 bg-ember/10 px-3 text-xs text-text transition-colors hover:bg-ember/20 motion-reduce:transition-none"
            >
              {label(code)}{' '}
              <span aria-hidden="true" className="text-muted">
                ×
              </span>
            </button>
          ))
        )}
        {selected.length > 0 && (
          <button
            type="button"
            onClick={() => onChange([])}
            className="min-h-9 px-2 text-xs text-muted underline underline-offset-4 hover:text-text"
          >
            Use worldwide
          </button>
        )}
      </div>
      <details className="rounded-md border border-line bg-ground open:border-ember/30">
        <summary className="cursor-pointer px-3 py-3 text-sm">
          Choose countries{' '}
          <span className="ml-2 text-xs text-muted">
            {selected.length} / {MAX_RESEARCH_COUNTRIES}
          </span>
        </summary>
        <div className="space-y-3 border-t border-line p-3">
          <TextField
            label="Search countries"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Country name or code"
          />
          <div
            className="max-h-52 overflow-y-auto overscroll-contain"
            aria-label="Available countries"
          >
            {matches.map((country) => (
              <label
                key={country.iso2}
                className="flex min-h-10 cursor-pointer items-center gap-3 rounded px-2 text-sm hover:bg-surface has-disabled:cursor-not-allowed has-disabled:opacity-50"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(country.iso2)}
                  disabled={
                    !selected.includes(country.iso2) && selected.length >= MAX_RESEARCH_COUNTRIES
                  }
                  onChange={(event) =>
                    onChange(
                      event.target.checked
                        ? [...selected, country.iso2]
                        : selected.filter((value) => value !== country.iso2),
                    )
                  }
                  className="h-4 w-4 accent-ember"
                />
                {country.name}{' '}
                <span className="ml-auto font-mono text-xs text-muted">{country.iso2}</span>
              </label>
            ))}
            {matches.length === 0 && (
              <p className="py-3 text-sm text-muted">No matching countries.</p>
            )}
          </div>
          {selected.length >= MAX_RESEARCH_COUNTRIES && (
            <p role="status" className="text-xs text-muted">
              Eight countries selected. Remove one to add another.
            </p>
          )}
        </div>
      </details>
    </fieldset>
  );
}
