import type { ViewMode } from '@/stores/globe';

export interface ModeToolbarProps {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
}

const options: { value: ViewMode; label: string; shortcut: string }[] = [
  { value: 'globe', label: 'Globe', shortcut: 'G' },
  { value: 'map', label: 'Map', shortcut: 'M' },
];

/** Segmented Globe / Map toggle floating over the view. */
export function ModeToolbar({ mode, onChange }: ModeToolbarProps) {
  return (
    <div
      role="group"
      aria-label="View mode"
      className="absolute top-3 left-3 z-10 flex overflow-hidden rounded-md border border-line bg-surface/90 backdrop-blur"
    >
      {options.map((option) => {
        const active = option.value === mode;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            title={`${option.label} (${option.shortcut})`}
            onClick={() => {
              onChange(option.value);
            }}
            className={`px-3 py-1.5 text-sm transition-colors ${
              active ? 'bg-ember text-ground' : 'text-muted hover:bg-surface-2 hover:text-text'
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
