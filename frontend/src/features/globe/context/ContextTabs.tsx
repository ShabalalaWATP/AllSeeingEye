import { useState, type ReactNode } from 'react';

/** Only the active content mounts, so context feeds remain strictly on demand. */
export function ContextTabs({
  label,
  primaryLabel,
  secondaryLabel,
  primary,
  secondary,
}: {
  label: string;
  primaryLabel: string;
  secondaryLabel: string;
  primary: ReactNode;
  secondary: ReactNode;
}) {
  const [secondaryOpen, setSecondaryOpen] = useState(false);
  return (
    <>
      <div
        role="group"
        aria-label={label}
        className="grid grid-cols-2 gap-1 border-b border-line p-2"
      >
        {[primaryLabel, secondaryLabel].map((value, index) => (
          <button
            key={value}
            type="button"
            aria-pressed={secondaryOpen === (index === 1)}
            onClick={() => setSecondaryOpen(index === 1)}
            className="min-h-10 rounded px-2 text-xs text-muted aria-pressed:bg-cyan/10 aria-pressed:text-cyan"
          >
            {value}
          </button>
        ))}
      </div>
      {secondaryOpen ? secondary : primary}
    </>
  );
}
