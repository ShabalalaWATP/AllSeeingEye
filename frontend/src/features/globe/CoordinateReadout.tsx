import { useEffect, useState } from 'react';

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
export function CoordinateReadout({ engine }: { engine: GlobeEngineHandle }) {
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
  const text = formatCoordinate(position);

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
      title="Click to copy"
      onClick={() => void copy()}
      className="absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-md border border-line bg-surface/90 px-2 py-1 font-mono text-[11px] text-muted backdrop-blur hover:text-text"
    >
      {copied ? 'Copied' : text}
    </button>
  );
}
