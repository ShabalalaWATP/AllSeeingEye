import { Children, isValidElement, useEffect, useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { MapControlLabel } from './MapControlLabel';
import { MapControlIcon } from './MapControlIcon';
import type { ControlIcon } from './MapControlIcon';
import './mapToolShell.css';

const CAPTIONS: Readonly<Record<string, string>> = {
  'Map style': 'Style',
  'Event time': 'Time',
  Measure: 'Measure',
  'Route planner': 'Route',
  'RF coverage': 'RF',
  'Research area': 'Area',
};

interface PanelProps {
  label: string;
  icon: ControlIcon;
  side?: 'left' | 'right';
  children: ReactNode;
  entry?: boolean;
  caption?: string;
  size?: 'medium';
  /** The layer this panel controls is shown, so the rail button stays lit while closed. */
  on?: boolean;
  /** Runs when the rail button opens the panel, before it renders. */
  onOpen?: () => void;
}
export function ControlPanel({ children }: PanelProps) {
  return children;
}

/** Non-modal tools leave map gestures available, including while measuring. */
export function GlobeControls({
  children,
  layers,
  navigation,
  onActiveChange,
}: {
  children: ReactNode;
  layers:
    | ReactNode
    | ((
        open: (label: string, button: HTMLButtonElement) => void,
        active: string | null,
      ) => ReactNode);
  navigation?: ReactNode;
  onActiveChange?: (label: string | null) => void;
}) {
  const [active, setActive] = useState<string | null>(null);
  const changed = useRef(onActiveChange);
  useEffect(() => {
    changed.current = onActiveChange;
  });
  useEffect(() => {
    changed.current?.(active);
  }, [active]);
  const id = useId();
  const [opener, setOpener] = useState<HTMLButtonElement | null>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const panels = Children.toArray(children).filter(isValidElement<PanelProps>);
  const selected = panels.find((panel) => panel.props.label === active);
  const close = () => {
    setActive(null);
    opener?.focus();
  };
  useEffect(() => {
    if (!active) return;
    closeButton.current?.focus();
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !event.defaultPrevented) {
        setActive(null);
        opener?.focus();
      }
    };
    document.addEventListener('keydown', dismiss);
    return () => document.removeEventListener('keydown', dismiss);
  }, [active, opener]);
  const panelButtons = (side: 'left' | 'right') =>
    panels
      .filter((panel) => panel.props.entry !== false && (panel.props.side ?? 'right') === side)
      .map(({ props }) => (
        <MapControlLabel key={props.label} label={props.label}>
          <button
            type="button"
            className={`map-icon-button ${(props.caption ?? CAPTIONS[props.label]) ? 'map-style-button' : ''}`}
            aria-label={props.label}
            title={props.label}
            aria-expanded={active === props.label}
            aria-controls={active === props.label ? id : undefined}
            data-on={props.on ? 'true' : undefined}
            onClick={(event) => {
              setOpener(event.currentTarget);
              if (active !== props.label) props.onOpen?.();
              setActive(active === props.label ? null : props.label);
            }}
          >
            <MapControlIcon name={props.icon} />
            {(props.caption ?? CAPTIONS[props.label]) && (
              <span className="map-style-label">{props.caption ?? CAPTIONS[props.label]}</span>
            )}
          </button>
        </MapControlLabel>
      ));
  return (
    <>
      <div className="map-layer-rail" role="group" aria-label="Map layers">
        {panelButtons('left')}
        <div className="map-rail-divider" />
        {typeof layers === 'function'
          ? layers((label, button) => {
              setOpener(button);
              setActive(active === label ? null : label);
            }, active)
          : layers}
      </div>
      <div className="map-tool-rail" role="group" aria-label="Map tools">
        {panelButtons('right')}
        {navigation}
      </div>
      {selected && (
        <section
          id={id}
          aria-label={active ?? undefined}
          className="map-tool-panel"
          data-side={selected.props.side ?? 'right'}
          data-size={selected.props.size}
        >
          <header className="map-tool-heading">
            <span className="map-tool-heading-icon" aria-hidden="true">
              <MapControlIcon name={selected.props.icon} />
            </span>
            <h2>{active}</h2>
            <button
              ref={closeButton}
              type="button"
              aria-label="Close tool"
              onClick={close}
              className="map-icon-button"
            >
              <MapControlIcon name="close" />
            </button>
          </header>
          <div key={active} className="map-tool-content">
            {selected.props.children}
          </div>
        </section>
      )}
    </>
  );
}
