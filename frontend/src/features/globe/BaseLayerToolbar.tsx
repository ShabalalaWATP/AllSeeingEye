import { useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';

import type { BaseLayer } from '@/stores/globe';

import { BASE_LAYER_OPTIONS } from './engine/baseLayers';

export interface BaseLayerToolbarProps {
  value: BaseLayer;
  initialExpanded?: boolean;
  /** Whether the server proxies Ordnance Survey tiles (it needs a key). */
  osAvailable: boolean;
  onChange: (layer: BaseLayer) => void;
}

/** A compact disclosure keeps the globe clear while making every map choice discoverable. */
export function BaseLayerToolbar({
  value,
  osAvailable,
  onChange,
  initialExpanded = false,
}: BaseLayerToolbarProps) {
  const [open, setOpen] = useState(initialExpanded);
  const panelId = useId();
  const hintId = useId();
  const osHintId = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const selected =
    BASE_LAYER_OPTIONS.find((option) => option.id === value) ?? BASE_LAYER_OPTIONS[0];
  const imagery = value === 'satellite' || value === 'hybrid';
  const closeOnEscape = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      setOpen(false);
      trigger.current?.focus();
    }
  };

  return (
    <div className="rounded-md border border-line bg-surface/95 backdrop-blur">
      <button
        ref={trigger}
        type="button"
        aria-label={`Map style: ${selected.label}`}
        aria-expanded={open}
        aria-controls={panelId}
        onKeyDown={closeOnEscape}
        onClick={() => {
          setOpen(!open);
        }}
        className="flex min-h-11 w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-left text-sm text-text transition-colors hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember"
      >
        <span className="flex min-w-0 items-center gap-2">
          <svg
            viewBox="0 0 20 20"
            fill="none"
            aria-hidden="true"
            className="size-4 shrink-0 text-ember"
          >
            <path
              d="m10 2 8 4-8 4-8-4 8-4ZM2 10l8 4 8-4M2 14l8 4 8-4"
              stroke="currentColor"
              strokeWidth="1.25"
              strokeLinejoin="round"
            />
          </svg>
          <span className="text-muted">Map style</span>
          <span className="truncate font-medium">{selected.label}</span>
        </span>
        <svg
          viewBox="0 0 12 12"
          fill="none"
          aria-hidden="true"
          className={`size-3 shrink-0 text-muted transition-transform motion-reduce:transition-none ${open ? 'rotate-180' : ''}`}
        >
          <path d="m2 4 4 4 4-4" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      </button>
      {open && (
        <div
          id={panelId}
          role="group"
          aria-label="Map style settings"
          className="border-t border-line"
        >
          <fieldset aria-describedby={hintId} className="m-0 min-w-0 border-0 p-1">
            <legend className="sr-only">Base layer</legend>
            {BASE_LAYER_OPTIONS.map((option) => {
              const unavailable = option.needsOs && !osAvailable;
              return (
                <label
                  key={option.id}
                  className={`flex min-h-11 items-center gap-2 rounded px-2 text-sm transition-colors lg:min-h-9 ${
                    unavailable
                      ? 'cursor-not-allowed text-muted'
                      : 'cursor-pointer text-text hover:bg-surface-2'
                  } ${option.id === value ? 'bg-surface-2' : ''}`}
                >
                  <input
                    type="radio"
                    name={panelId}
                    value={option.id}
                    checked={option.id === value}
                    disabled={unavailable}
                    aria-label={option.label}
                    aria-describedby={unavailable ? osHintId : undefined}
                    onKeyDown={closeOnEscape}
                    onChange={() => {
                      onChange(option.id);
                    }}
                    className="size-3.5 shrink-0 accent-ember focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember"
                  />
                  <span className="flex-1">{option.label}</span>
                  {option.needsOs && (
                    <span className="text-[10px] tracking-wide text-muted">GB</span>
                  )}
                </label>
              );
            })}
          </fieldset>
          <div
            id={hintId}
            className="space-y-2 border-t border-line px-3 py-2.5 text-xs leading-relaxed text-muted"
          >
            <p className="font-medium text-text">{selected.coverage}</p>
            <p>{selected.description}</p>
            {imagery && (
              <p>
                Non-commercial use only.{' '}
                <a
                  className="underline underline-offset-2 hover:text-text"
                  href="https://creativecommons.org/licenses/by-nc-sa/4.0/"
                  onKeyDown={closeOnEscape}
                  target="_blank"
                  rel="noreferrer"
                >
                  Imagery licence
                </a>
              </p>
            )}
            {selected.needsOs && (
              <p>Zoom into Great Britain to see OS mapping. Uses OpenData detail only.</p>
            )}
          </div>
          {!osAvailable && (
            <p
              id={osHintId}
              className="border-t border-line px-3 py-2 text-xs leading-relaxed text-muted"
            >
              OS maps are unavailable. An administrator must configure the Ordnance Survey
              connection.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
