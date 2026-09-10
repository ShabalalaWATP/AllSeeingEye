import { Fragment, useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';

import type { BaseLayer } from '@/stores/globe';
import { MapToolIntro } from '@/components/maps/MapToolIntro';

import { BASE_LAYER_OPTIONS } from './engine/baseLayers';
import './referenceTools.css';

export interface BaseLayerToolbarProps {
  value: BaseLayer;
  initialExpanded?: boolean;
  /** The shared map drawer already owns disclosure and Escape handling. */
  embedded?: boolean;
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
  embedded = false,
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
    if (event.key === 'Escape' && !embedded) {
      event.stopPropagation();
      setOpen(false);
      trigger.current?.focus();
    }
  };

  return (
    <div className="map-tool-workspace">
      {embedded ? (
        <MapToolIntro
          title="Basemap"
          description="Choose the surface beneath your event layers."
          status={selected.label}
          statusActive
        />
      ) : (
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
          className="map-tool-secondary flex w-full items-center justify-between gap-2 text-left"
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
      )}
      {(open || embedded) && (
        <div id={panelId} role="group" aria-label="Map style settings" className="map-tool-section">
          <p className="map-tool-help">Style swatches are illustrative, not map previews.</p>
          <fieldset aria-describedby={hintId} className="m-0 min-w-0 border-0 p-0">
            <legend className="sr-only">Base layer</legend>
            {BASE_LAYER_OPTIONS.map((option) => {
              const unavailable = option.needsOs && !osAvailable;
              return (
                <Fragment key={option.id}>
                  {option.id === 'os_road' && (
                    <div className="map-tool-section map-reference-footnote">
                      <div className="flex items-start justify-between gap-2">
                        <p className="map-tool-section-title">Ordnance Survey · Great Britain</p>
                        <span className="map-reference-badge">
                          {osChecking
                            ? 'Checking'
                            : osError
                              ? 'Check failed'
                              : osAvailable
                                ? 'Configured'
                                : 'Connection required'}
                        </span>
                      </div>
                      <p
                        id={osHintId}
                        role={osError ? 'alert' : 'status'}
                        className="map-tool-help"
                      >
                        {osChecking
                          ? 'Checking the server’s Ordnance Survey configuration…'
                          : osError
                            ? 'Configuration check failed. Try again to check whether OS maps are available.'
                            : osAvailable
                              ? 'The server has an OS key configured. This check does not test tile delivery. Coverage is Great Britain at zoom 7–16.'
                              : 'OS maps are unavailable. An administrator must configure an OS Data Hub Maps API key before these styles can be selected.'}
                      </p>
                      {!osAvailable && !osChecking && !osError && (
                        <details className="map-tool-disclosure">
                          <summary>How to enable OS maps</summary>
                          <ol className="map-tool-help mt-2 list-decimal space-y-2 pl-4">
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
                            className="map-tool-text-button mt-2 inline-block"
                          >
                            OS Data Hub setup guide
                          </a>
                        </details>
                      )}
                      {onCheckOs && (
                        <button
                          type="button"
                          className="map-tool-secondary"
                          disabled={osChecking}
                          onClick={onCheckOs}
                        >
                          Check configuration again
                        </button>
                      )}
                    </div>
                  )}
                  <label className="map-reference-choice">
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
                    <svg
                      aria-hidden="true"
                      viewBox="0 0 42 30"
                      data-style={option.id}
                      className="map-reference-swatch"
                    >
                      <path
                        d="M0 9 17 4 29 12 42 5v14L28 26 13 20 0 26Z"
                        fill="currentColor"
                        opacity=".24"
                      />
                      <path
                        d="M-2 27 12 18 19 4 25-2M13 32 24 19l20-6M-2 9l46 15"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                      />
                    </svg>
                    <span className="map-reference-choice-title">{option.label}</span>
                    {option.needsOs && (
                      <span className="map-reference-badge">
                        {unavailable ? 'Unavailable' : 'GB'}
                      </span>
                    )}
                  </label>
                </Fragment>
              );
            })}
          </fieldset>
        </div>
      )}
      <div id={hintId} className="map-tool-section map-reference-footnote">
        <p className="map-tool-section-title">{selected.coverage}</p>
        <p className="map-tool-help">{selected.description}</p>
        {imagery && (
          <p className="map-tool-help">
            Non-commercial use only.{' '}
            <a
              className="map-tool-text-button"
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
          <p className="map-tool-help">
            Zoom into Great Britain to see OS mapping. Uses OpenData detail only.
          </p>
        )}
      </div>
    </div>
  );
}
