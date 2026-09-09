import { Fragment, useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';

import type { BaseLayer } from '@/stores/globe';

import { BASE_LAYER_OPTIONS } from './engine/baseLayers';

export interface BaseLayerToolbarProps {
  value: BaseLayer;
  initialExpanded?: boolean;
  /** Whether the server proxies Ordnance Survey tiles (it needs a key). */
  osAvailable: boolean;
  osChecking?: boolean;
  osError?: string | null;
  onCheckOs?: () => void;
  onChange: (layer: BaseLayer) => void;
}

/** A compact disclosure keeps the globe clear while making every map choice discoverable. */
export function BaseLayerToolbar({
  value,
  osAvailable,
  osChecking = false,
  osError = null,
  onCheckOs,
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
                <Fragment key={option.id}>
                  {option.id === 'os_road' && (
                    <div className="mt-2 space-y-2 border-t border-line px-2 py-3 text-xs leading-relaxed">
                      <div className="flex items-start justify-between gap-2">
                        <p className="font-medium text-text">Ordnance Survey · Great Britain</p>
                        <span className="rounded border border-line px-1.5 py-0.5 text-[10px] text-muted">
                          {osChecking
                            ? 'Checking'
                            : osError
                              ? 'Check failed'
                              : osAvailable
                                ? 'Configured'
                                : 'Connection required'}
                        </span>
                      </div>
                      <p id={osHintId} role={osError ? 'alert' : 'status'} className="text-muted">
                        {osChecking
                          ? 'Checking the server’s Ordnance Survey configuration…'
                          : osError
                            ? 'Configuration check failed. Try again to check whether OS maps are available.'
                            : osAvailable
                              ? 'The server has an OS key configured. This check does not test tile delivery. Coverage is Great Britain at zoom 7–16.'
                              : 'OS maps are unavailable. An administrator must configure an OS Data Hub Maps API key before these styles can be selected.'}
                      </p>
                      {!osAvailable && !osChecking && !osError && (
                        <details className="text-muted">
                          <summary className="cursor-pointer text-text">
                            How to enable OS maps
                          </summary>
                          <ol className="mt-2 list-decimal space-y-1 pl-4">
                            <li>Create an OS Data Hub project with the Maps API enabled.</li>
                            <li>
                              The server administrator adds its key as <code>ASE_OS_MAPS_KEY</code>{' '}
                              in the backend environment and restarts the API.
                            </li>
                            <li>Check configuration again here. The key stays on the server.</li>
                          </ol>
                          <a
                            href="https://docs.os.uk/os-apis/accessing-os-apis/os-maps-api/getting-started"
                            target="_blank"
                            rel="noreferrer"
                            className="mt-2 inline-block underline underline-offset-2"
                          >
                            OS Data Hub setup guide
                          </a>
                        </details>
                      )}
                      {onCheckOs && (
                        <button
                          type="button"
                          className="rounded border border-line px-2 py-1.5 text-text hover:bg-surface-2 disabled:opacity-50"
                          disabled={osChecking}
                          onClick={onCheckOs}
                        >
                          Check configuration again
                        </button>
                      )}
                    </div>
                  )}
                  <label
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
                      aria-describedby={option.needsOs ? osHintId : undefined}
                      onKeyDown={closeOnEscape}
                      onChange={() => {
                        onChange(option.id);
                      }}
                      className="size-3.5 shrink-0 accent-ember focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember"
                    />
                    <span className="flex-1">{option.label}</span>
                    {option.needsOs && (
                      <span className="text-[10px] tracking-wide text-muted">
                        {unavailable ? 'Unavailable' : 'GB'}
                      </span>
                    )}
                  </label>
                </Fragment>
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
        </div>
      )}
    </div>
  );
}
