import { useEffect, useRef } from 'react';
import type { RadarAttackSnapshot } from '@/lib/api/cyber';
import { isHttpUrl } from '@/lib/urls';
import type { RadarAttackCountry } from './radarAttackCountries';

export function RadarAttackInspector({
  row,
  snapshot,
  onClose,
}: {
  row: RadarAttackCountry;
  snapshot: RadarAttackSnapshot;
  onClose: () => void;
}) {
  const button = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const opener = document.activeElement;
    button.current?.focus();
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
      aria-label="Cloudflare traffic country details"
      className="map-details-inspector absolute bottom-16 right-16 z-20 max-h-[calc(100%-8rem)] w-80 max-w-[calc(100%-5rem)] overflow-y-auto rounded-lg border border-violet-400/50 bg-ground p-4 shadow-xl"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="text-2xs uppercase tracking-wider text-violet-300">
            Cloudflare observed traffic
          </p>
          <h2 className="mt-1 text-sm font-medium">{row.country.name}</h2>
        </div>
        <button
          ref={button}
          type="button"
          aria-label="Close Cloudflare traffic details"
          onClick={onClose}
          className="min-h-9 px-2 text-muted"
        >
          ×
        </button>
      </header>
      <dl className="mt-4 grid grid-cols-[1fr_auto] gap-2 text-xs">
        <dt>Network layer (L3/4), mitigated bytes</dt>
        <dd className="font-mono text-violet-200">
          {row.layer3 === null ? 'Not in top 10' : `${row.layer3.toFixed(1)}%`}
        </dd>
        <dt>Application layer (L7), mitigated requests</dt>
        <dd className="font-mono text-violet-200">
          {row.layer7 === null ? 'Not in top 10' : `${row.layer7.toFixed(1)}%`}
        </dd>
      </dl>
      <p className="mt-4 text-xs leading-5 text-muted">
        Shares of Cloudflare-observed mitigated traffic across target billing countries in each
        layer’s stated period. The marker is a country reference, not an attack location, attacker
        origin, incident count or national risk score.
      </p>
      <ul className="mt-3 space-y-1 text-[11px] text-muted">
        {snapshot.layers.map((layer) => (
          <li key={layer.layer}>
            {layer.layer === 'layer3' ? 'L3/4' : 'L7'}:{' '}
            {new Date(layer.period_from).toLocaleDateString('en-GB', { timeZone: 'UTC' })} to{' '}
            {new Date(layer.period_to).toLocaleDateString('en-GB', { timeZone: 'UTC' })} UTC
          </li>
        ))}
      </ul>
      {snapshot.status === 'stale' && (
        <p className="mt-2 text-xs text-amber-200">Previously collected data; refresh failed.</p>
      )}
      {isHttpUrl(snapshot.source_url) && (
        <a
          href={snapshot.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-block text-xs text-cyan underline"
        >
          Cloudflare Radar source
        </a>
      )}
      <p className="mt-1 text-2xs text-muted">Cloudflare Radar · CC BY-NC 4.0</p>
    </aside>
  );
}
