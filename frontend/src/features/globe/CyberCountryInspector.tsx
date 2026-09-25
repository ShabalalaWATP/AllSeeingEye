import { useEffect, useRef } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { CYBER_KIND_LABELS, cyberKind } from '@/lib/cyber';
import type { CyberCountryContext } from './cyberCountryContext';

export function CyberCountryInspector({
  group,
  onClose,
  onSelect,
}: {
  group: CyberCountryContext;
  onClose: () => void;
  onSelect: (event: LiveEvent) => void;
}) {
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const opener = document.activeElement;
    close.current?.focus();
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !event.defaultPrevented) {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', dismiss);
    return () => {
      window.removeEventListener('keydown', dismiss);
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, [onClose]);
  return (
    <aside
      aria-label="Cyber country context details"
      className="map-details-inspector absolute bottom-16 right-16 z-20 max-h-[calc(100%-8rem)] w-80 max-w-[calc(100%-5rem)] overflow-y-auto rounded-lg border border-line bg-ground p-4 shadow-xl"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="text-2xs uppercase tracking-wider text-cyan">Cyber country context</p>
          <h2 className="mt-1 text-sm font-medium">{group.country.name}</h2>
        </div>
        <button
          ref={close}
          type="button"
          onClick={onClose}
          aria-label="Close cyber country context"
          className="min-h-9 px-2 text-muted"
        >
          ×
        </button>
      </header>
      <p className="mt-3 text-xs text-muted">
        This is a country reference, not an incident coordinate. The marker groups{' '}
        {group.events.length} collected source-attributed records. It does not locate attackers or
        establish attack paths.
      </p>
      <p className="mt-2 text-[11px] text-muted">
        Claims remain unverified; connectivity signal drops do not establish cyberattack causation
        or current outage status. Multiple records may describe the same event.
      </p>
      <ul className="mt-3 space-y-2">
        {group.events.slice(0, 25).map((event) => (
          <li key={event.id}>
            <button
              type="button"
              onClick={() => onSelect(event)}
              className="w-full rounded border border-line p-3 text-left text-xs hover:border-cyan"
            >
              <span className="block">{event.title}</span>
              <span className="mt-1 block text-2xs text-muted">
                {CYBER_KIND_LABELS[cyberKind(event)]} · {event.source_id.replaceAll('_', ' ')}
              </span>
            </button>
          </li>
        ))}
      </ul>
      {group.events.length > 25 && (
        <p className="mt-2 text-2xs text-muted">Showing the first 25 records in this snapshot.</p>
      )}
    </aside>
  );
}
