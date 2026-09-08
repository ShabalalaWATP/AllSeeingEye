import { useEffect, useState } from 'react';
import { BNG_NOTE, formatBritishGrid } from '@/lib/map/britishGrid';

import type { CursorPosition } from './engine/MapEngine';
import type { GlobeEngineHandle } from './useGlobeEngine';

export function formatCoordinate(position: CursorPosition): string {
  const lat = `${Math.abs(position.lat).toFixed(4)}° ${position.lat >= 0 ? 'N' : 'S'}`;
  const lon = `${Math.abs(position.lon).toFixed(4)}° ${position.lon >= 0 ? 'E' : 'W'}`;
  return `${lat}, ${lon}`;
}

/**
 * The cursor's position in WGS84, kept after the pointer leaves the map so the value
 * can be clicked and copied.
 */
export function CoordinateReadout({
  engine,
  bng = false,
}: {
  engine: GlobeEngineHandle;
  bng?: boolean;
}) {
  const [position, setPosition] = useState<CursorPosition | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => engine.onCursor(setPosition), [engine]);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => {
      setCopied(false);
    }, 1500);
    return () => {
      window.clearTimeout(timer);
    };
  }, [copied]);

  if (position === null) return null;
  const grid = bng ? formatBritishGrid(position) : null;
  const text = grid ?? formatCoordinate(position);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <button
      type="button"
      aria-label="Copy coordinates"
      title={bng ? `${BNG_NOTE} Click to copy.` : 'Click to copy'}
      onClick={() => void copy()}
      className="map-coordinate-readout absolute left-1/2 z-10 min-h-11 max-w-[calc(100%-1.5rem)] -translate-x-1/2 rounded-md border border-line bg-surface/90 px-2 py-1 font-mono text-[11px] whitespace-nowrap text-muted backdrop-blur hover:text-text lg:min-h-0"
    >
      {copied ? 'Copied' : text}
      {bng && grid === null && <span className="ml-2 text-muted">Outside BNG extent</span>}
    </button>
  );
}
