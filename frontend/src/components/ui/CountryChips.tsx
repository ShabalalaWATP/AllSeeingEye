export interface CountryOption {
  code: string;
  count: number;
}

const ORGANISATIONS = 'ORG';
let names: Intl.DisplayNames | null | undefined;

/** Region name from the ISO code, falling back to the code itself where ICU data is missing. */
export function regionName(code: string): string {
  if (code === ORGANISATIONS) return 'Organisations';
  try {
    names ??= new Intl.DisplayNames(['en-GB'], { type: 'region' });
    return names.of(code) ?? code;
  } catch {
    names = null;
    return code;
  }
}

/** Multi-select country chips; an empty selection means every country. */
export function CountryChips({
  label,
  options,
  selected,
  onToggle,
  onClear,
}: {
  label: string;
  options: readonly CountryOption[];
  selected: ReadonlySet<string>;
  onToggle: (code: string) => void;
  onClear: () => void;
}) {
  const chip = (active: boolean) =>
    `min-h-8 rounded-full border px-2.5 py-1 text-[11px] leading-none transition-colors ${
      active
        ? 'border-cyan/70 bg-cyan/15 text-text'
        : 'border-line text-muted hover:border-cyan/40 hover:text-text'
    }`;
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-1.5">
      <button
        type="button"
        aria-pressed={selected.size === 0}
        onClick={onClear}
        className={chip(selected.size === 0)}
      >
        All
      </button>
      {options.map((option) => (
        <button
          key={option.code}
          type="button"
          aria-pressed={selected.has(option.code)}
          onClick={() => onToggle(option.code)}
          title={regionName(option.code)}
          className={chip(selected.has(option.code))}
        >
          {option.code === ORGANISATIONS ? 'Orgs' : option.code}
          <span className="ml-1 font-mono text-[10px] opacity-70">{option.count}</span>
        </button>
      ))}
    </div>
  );
}

/** Country options for a set of figures, organisations grouped under one key. */
export function countryOptions(items: readonly { country_iso: string | null }[]): CountryOption[] {
  const counts = new Map<string, number>();
  for (const item of items) {
    const code = item.country_iso ?? ORGANISATIONS;
    counts.set(code, (counts.get(code) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([code, count]) => ({ code, count }))
    .sort((a, b) =>
      a.code === ORGANISATIONS ? 1 : b.code === ORGANISATIONS ? -1 : a.code.localeCompare(b.code),
    );
}

export function matchesCountries(
  item: { country_iso: string | null },
  selected: ReadonlySet<string>,
): boolean {
  return selected.size === 0 || selected.has(item.country_iso ?? ORGANISATIONS);
}
