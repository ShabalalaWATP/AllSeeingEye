import { useEffect, useRef } from 'react';
import type { LocalFeature } from '@/lib/map/geoJsonTypes';
export interface MapObjectSelection {
  feature: LocalFeature;
  title: string;
  notes: string[];
}
export function MapObjectDetails({
  value,
  onClose,
}: {
  value: MapObjectSelection;
  onClose: () => void;
}) {
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const opener = document.activeElement;
    close.current?.focus();
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', escape);
    return () => {
      window.removeEventListener('keydown', escape);
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, [onClose]);
  return (
    <section aria-label="Selected map object" className="border-t border-line p-3 text-sm">
      <div className="flex justify-between gap-3">
        <h4 className="font-medium">{value.title}</h4>
        <button ref={close} type="button" onClick={onClose} className="text-xs underline">
          Close map object details
        </button>
      </div>
      <p className="mt-2 break-words">
        {value.feature.properties.label || 'Unlabelled geometry'} / {value.feature.geometry.type}
      </p>
      {value.notes.map((note, index) => (
        <p key={index} className="mt-1 break-words text-xs text-muted">
          {note}
        </p>
      ))}
    </section>
  );
}
