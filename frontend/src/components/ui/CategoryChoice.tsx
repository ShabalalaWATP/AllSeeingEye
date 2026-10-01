import { useId } from 'react';

import type { Category } from '@/lib/api/eventSchemas';
import { CATEGORY_STYLES, ORDERED_CATEGORIES } from '@/lib/categories';

/**
 * Event categories as an explicit choice: every category, or specific ones from the
 * canonical list with plain labels. Unknown saved values stay visible with a Remove button
 * so they are never dropped without the person seeing them.
 */
export function CategoryChoice({
  all,
  value,
  onAllChange,
  onChange,
  error,
  id,
}: {
  all: boolean;
  value: readonly string[];
  onAllChange: (all: boolean) => void;
  onChange: (categories: string[]) => void;
  error?: string | undefined;
  id?: string | undefined;
}) {
  const name = useId();
  const errorId = useId();
  const unknown = value.filter((item) => !(item in CATEGORY_STYLES));
  const toggle = (category: Category, checked: boolean) =>
    onChange(checked ? [...value, category] : value.filter((item) => item !== category));
  return (
    <fieldset
      id={id}
      className="min-w-0 space-y-2"
      aria-describedby={error === undefined ? undefined : errorId}
    >
      <legend className="text-sm font-medium">Event categories</legend>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
        <label className="flex min-h-9 items-center gap-2">
          <input
            type="radio"
            name={name}
            checked={all}
            onChange={() => onAllChange(true)}
            className="accent-ember"
          />
          All event categories
        </label>
        <label className="flex min-h-9 items-center gap-2">
          <input
            type="radio"
            name={name}
            checked={!all}
            onChange={() => onAllChange(false)}
            className="accent-ember"
          />
          Specific categories
        </label>
      </div>
      {error !== undefined && (
        <p id={errorId} className="text-sm text-critical">
          {error}
        </p>
      )}
      {!all && (
        <div role="group" aria-label="Categories to watch" className="grid gap-1 sm:grid-cols-3">
          {ORDERED_CATEGORIES.map((category) => (
            <label key={category} className="flex min-h-9 items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={value.includes(category)}
                onChange={(event) => toggle(category, event.target.checked)}
                className="h-4 w-4 accent-ember"
              />
              {CATEGORY_STYLES[category].label}
            </label>
          ))}
        </div>
      )}
      {!all &&
        unknown.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => onChange(value.filter((entry) => entry !== item))}
            className="mr-2 min-h-9 rounded-md border border-critical/40 px-3 text-xs text-text"
          >
            Remove unknown category “{item}”
          </button>
        ))}
    </fieldset>
  );
}
