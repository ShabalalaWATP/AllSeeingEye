import { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import type { ReactNode } from 'react';
import type { FlightFilter } from './flightFilters';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { TrafficList } from './TrafficList';

/** A disclosure attached to the flight switch; its portal escapes the scrolling rail. */
export function FlightLayerControl({
  children,
  filter = 'all',
  onChange,
  count,
  kind = 'aircraft',
  events,
  available,
  onSelect,
  selectionDisabled = false,
}: {
  children: ReactNode;
  filter?: FlightFilter;
  onChange?: ((value: FlightFilter) => void) | undefined;
  selectionDisabled?: boolean;
  count: number;
  kind?: 'aircraft' | 'vessels';
  events?: readonly LiveEvent[];
  available?: number | undefined;
  onSelect?: ((event: LiveEvent) => void) | undefined;
}) {
  const label = kind === 'aircraft' ? 'Flight filters' : 'Boat list';
  const [position, setPosition] = useState<{ left: number; top: number } | null>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const id = useId();
  const close = () => {
    setPosition(null);
    trigger.current?.focus();
  };
  useEffect(() => {
    if (!position) return;
    closeButton.current?.focus();
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setPosition(null);
        trigger.current?.focus();
      }
    };
    const outside = (event: PointerEvent) => {
      if (
        event.target instanceof Node &&
        !panel.current?.contains(event.target) &&
        !trigger.current?.contains(event.target)
      )
        setPosition(null);
    };
    document.addEventListener('keydown', dismiss);
    document.addEventListener('pointerdown', outside);
    return () => {
      document.removeEventListener('keydown', dismiss);
      document.removeEventListener('pointerdown', outside);
    };
  }, [position]);
  return (
    <div className="flex flex-col items-center">
      {children}
      <button
        ref={trigger}
        type="button"
        aria-label={label}
        aria-expanded={position !== null}
        aria-controls={position ? id : undefined}
        title={
          kind === 'vessels'
            ? 'Search loaded vessels'
            : filter === 'military'
              ? 'Flight filters: military only'
              : 'Flight filters and aircraft list'
        }
        className={`flex h-6 w-10 items-center justify-center rounded text-[10px] hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-cyan ${filter === 'military' ? 'text-cyan' : 'text-muted'}`}
        onClick={(event) => {
          if (position) {
            close();
            return;
          }
          const rect = event.currentTarget.getBoundingClientRect();
          setPosition({
            left: Math.max(8, Math.min(rect.right + 8, window.innerWidth - 336)),
            top: Math.max(8, Math.min(rect.top, window.innerHeight - 560)),
          });
        }}
      >
        <span>{filter === 'military' ? 'MIL' : kind === 'vessels' ? 'LIST' : 'ALL'}</span>
        <span aria-hidden="true" className="ml-1">
          ▸
        </span>
      </button>
      {position &&
        createPortal(
          <section
            ref={panel}
            id={id}
            aria-label={label}
            style={position}
            className="fixed z-50 max-h-[calc(100vh-16px)] w-80 max-w-[calc(100vw-16px)] overflow-y-auto rounded-lg border border-line bg-ground p-3 text-text shadow-xl"
          >
            <header className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-medium">{kind === 'aircraft' ? 'Flights' : 'Boats'}</h2>
              <button
                ref={closeButton}
                type="button"
                aria-label={kind === 'aircraft' ? 'Close flight filters' : 'Close boat list'}
                onClick={close}
                className="px-2 py-1 text-muted hover:text-cyan"
              >
                ×
              </button>
            </header>
            {onChange && (
              <fieldset>
                <legend className="mb-2 text-xs text-muted">
                  {kind === 'aircraft' ? 'Aircraft shown' : 'Vessels shown'}
                </legend>
                {(['all', 'military'] as const).map((value) => (
                  <label
                    key={value}
                    className="flex min-h-10 cursor-pointer items-center gap-2 text-sm"
                  >
                    <input
                      type="radio"
                      name={id}
                      value={value}
                      checked={filter === value}
                      onChange={() => onChange(value)}
                      className="accent-cyan"
                    />
                    {value === 'all'
                      ? kind === 'aircraft'
                        ? 'All aircraft'
                        : 'All vessels'
                      : 'Military only'}
                  </label>
                ))}
              </fieldset>
            )}
            <p
              className={`my-2 text-xs ${kind === 'aircraft' ? 'text-amber-300' : 'text-fuchsia-300'}`}
            >
              {count}{' '}
              {kind === 'aircraft'
                ? 'provider-labelled military aircraft loaded'
                : 'vessels labelled as military operations'}
            </p>
            <p className="mt-2 text-xs leading-relaxed text-muted">
              {kind === 'aircraft' ? (
                <>
                  Classification comes from the public provider. Reception is incomplete; hidden
                  transponders and aircraft outside receiver coverage are not shown. This filter
                  does not establish a flight’s mission.
                </>
              ) : (
                <>
                  Purple identifies reported military operations from AIS ship type or an explicit
                  provider label. This does not verify naval ownership. Position and classification
                  coverage vary.
                </>
              )}
            </p>
            {events && onSelect && (
              <TrafficList
                events={events}
                kind={kind}
                available={available}
                selectionDisabled={selectionDisabled}
                onSelect={(event) => {
                  close();
                  onSelect(event);
                }}
              />
            )}
          </section>,
          document.body,
        )}
    </div>
  );
}
