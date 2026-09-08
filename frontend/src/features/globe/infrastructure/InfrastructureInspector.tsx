import { useEffect, useRef } from 'react';
import type { InfrastructureSelection } from './useInfrastructure';

export function InfrastructureInspector({
  selected,
  onClose,
}: {
  selected: InfrastructureSelection;
  onClose: () => void;
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
      aria-label="Infrastructure details"
      className="map-details-inspector absolute bottom-16 right-16 z-20 w-80 max-w-[calc(100%-5rem)] rounded-lg border border-line bg-ground p-4 shadow-xl"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-cyan">
            {selected.kind === 'station' ? 'Satellite ground station' : 'Undersea cable segment'}
          </p>
          <h2 className="mt-1 text-sm font-medium">{selected.item.name}</h2>
        </div>
        <button
          ref={close}
          type="button"
          onClick={onClose}
          aria-label="Close infrastructure details"
          className="px-2 py-1 text-muted hover:text-cyan"
        >
          ×
        </button>
      </header>
      {selected.kind === 'station' && (
        <p className="mt-3 text-xs text-muted">
          {selected.item.operator} · {selected.item.country}
        </p>
      )}
      <p className="mt-3 text-xs font-medium text-cyan">
        Approximate {selected.kind === 'station' ? 'location' : 'route'}
      </p>
      <p className="mt-2 text-xs leading-relaxed text-muted">{selected.item.note}</p>
      <p className="mt-2 text-xs leading-relaxed text-muted">
        {selected.kind === 'station'
          ? 'A public site or locality marker does not indicate current communications or activity.'
          : 'This segment is an incomplete map record, not proof of its condition, exact seabed route or operational status.'}
      </p>
      <a
        className="mt-3 inline-block text-xs text-cyan underline"
        href={selected.item.source_url}
        target="_blank"
        rel="noreferrer"
      >
        View public source
      </a>
    </aside>
  );
}
