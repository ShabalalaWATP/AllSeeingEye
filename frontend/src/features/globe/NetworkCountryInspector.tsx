import { useEffect, useRef } from 'react';
import { isHttpUrl } from '@/lib/urls';
import { utcDate } from './context/contextPresentation';
import type { NetworkCountryGroup } from './networkContext';

export function NetworkCountryInspector({
  group,
  onClose,
}: {
  group: NetworkCountryGroup;
  onClose: () => void;
}) {
  const closeButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const opener = document.activeElement;
    closeButton.current?.focus();
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
      aria-label="Network country details"
      className="map-details-inspector absolute bottom-16 right-16 z-20 max-h-[calc(100%-8rem)] w-80 max-w-[calc(100%-5rem)] overflow-y-auto rounded-lg border border-line bg-ground p-4 shadow-xl"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="text-2xs uppercase tracking-wider text-amber-300">Network signals</p>
          <h2 className="mt-1 text-sm font-medium">{group.country.name}</h2>
        </div>
        <button
          ref={closeButton}
          type="button"
          aria-label="Close network country details"
          onClick={onClose}
          className="min-h-9 px-2 text-muted"
        >
          ×
        </button>
      </header>
      <p className="mt-3 text-xs text-muted">
        Country reference for {group.events.length} provider-reported connectivity{' '}
        {group.events.length === 1 ? 'record' : 'records'}. The marker does not locate an outage or
        establish its cause, scale or current status.
      </p>
      <ul className="mt-3 space-y-2">
        {group.events.slice(0, 25).map((event) => (
          <li key={event.id} className="rounded border border-line p-3 text-xs">
            <span className="block text-text">{event.title}</span>
            <span className="mt-1 block text-2xs text-muted">
              Reported {utcDate(event.published_at)}
            </span>
            {isHttpUrl(event.url) && (
              <a
                href={event.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-block text-cyan underline underline-offset-2"
              >
                Open source
              </a>
            )}
          </li>
        ))}
      </ul>
      {group.events.length > 25 && (
        <p className="mt-2 text-2xs text-muted">Showing 25 of {group.events.length} records.</p>
      )}
    </aside>
  );
}
