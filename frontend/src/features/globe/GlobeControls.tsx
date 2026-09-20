import { Children, isValidElement, useEffect, useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { resolveMapPanel } from '@/lib/mapLayerDirectory';
import { MapControlLabel } from './MapControlLabel';
import { MapControlIcon } from './MapControlIcon';
import { MapToolChooser } from './MapToolChooser';
import { MapToolInspector } from './MapToolInspector';
import { DEFAULT_FAVOURITES, toolCaption, toolId } from './mapToolDefinitions';
import type { MapPanel, PanelProps } from './mapToolDefinitions';
import { readToolFavourites, writeToolFavourites } from './mapToolPreferences';
import './mapToolShell.css';

export function ControlPanel({ children }: PanelProps) {
  return children;
}
/** Non-modal tools leave map gestures available, including while measuring. */
export type OpenPanel = (label: string, button?: HTMLButtonElement | null) => void;

export function GlobeControls({
  children,
  layers,
  navigation,
  activity,
  onActiveChange,
  onPanelChange,
  requestedPanel,
  requestKey,
  initial = null,
}: {
  children: ReactNode | ((open: OpenPanel) => ReactNode);
  layers: ReactNode | ((open: OpenPanel, active: string | null) => ReactNode);
  navigation?: ReactNode;
  /** Compact active-mode controls remain available when the inspector is collapsed. */
  activity?: ReactNode;
  onActiveChange?: (label: string | null) => void;
  /** Called for user navigation only, never when replaying browser history. */
  onPanelChange?: (label: string | null) => void;
  requestedPanel?: string | null;
  requestKey?: string;
  /** Backwards-compatible external request. Changes are synchronised after mount. */
  initial?: string | null;
}) {
  const requested = requestedPanel === undefined ? initial : requestedPanel;
  const incoming = resolveMapPanel(requested) ?? requested;
  const [state, setState] = useState({
    requested: incoming,
    requestKey,
    active: incoming,
    collapsed: false,
    chooser: false,
  });
  if (state.requested !== incoming || state.requestKey !== requestKey) {
    setState({
      requested: incoming,
      requestKey,
      active: incoming,
      collapsed: false,
      chooser: false,
    });
  }
  const { active, collapsed, chooser } = state;
  const changed = useRef(onActiveChange);
  const navigated = useRef(onPanelChange);
  useEffect(() => {
    changed.current = onActiveChange;
    navigated.current = onPanelChange;
  });
  useEffect(() => {
    changed.current?.(active);
  }, [active]);
  const id = useId();
  const [opener, setOpener] = useState<HTMLButtonElement | null>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const chooserClose = useRef<HTMLButtonElement>(null);
  const toolsButton = useRef<HTMLButtonElement>(null);
  const [pins, setPins] = useState(readToolFavourites);
  const select = (label: string | null) => {
    setState((current) => ({ ...current, active: label, collapsed: false, chooser: false }));
    onPanelChange?.(label);
  };
  const openPanel: OpenPanel = (label, button) => {
    if (button) setOpener(button);
    select(active === label && !collapsed ? null : label);
  };
  const resolved = typeof children === 'function' ? children(openPanel) : children;
  const panels = Children.toArray(resolved).filter(isValidElement<PanelProps>);
  const selected = panels.find((panel) => panel.props.label === active);
  const right = panels.filter(
    ({ props }) => props.entry !== false && (props.side ?? 'right') === 'right',
  );
  const favourites =
    pins ?? (right.length <= 4 ? right.map(({ props }) => toolId(props)) : DEFAULT_FAVOURITES);
  const close = () => {
    select(null);
    if (opener?.isConnected) opener.focus();
    else toolsButton.current?.focus();
  };
  const dismissChooser = () => {
    setState((current) => ({ ...current, chooser: false }));
    toolsButton.current?.focus();
  };
  useEffect(() => {
    if (active) closeButton.current?.focus();
  }, [active, opener, requestKey]);
  useEffect(() => {
    if (chooser) chooserClose.current?.focus();
  }, [chooser]);
  useEffect(() => {
    if (!active && !chooser) return;
    const dismiss = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || event.defaultPrevented) return;
      if (chooser) {
        setState((current) => ({ ...current, chooser: false }));
        toolsButton.current?.focus();
      } else {
        setState((current) => ({ ...current, active: null, collapsed: false }));
        navigated.current?.(null);
        if (opener?.isConnected) opener.focus();
        else toolsButton.current?.focus();
      }
    };
    document.addEventListener('keydown', dismiss);
    return () => document.removeEventListener('keydown', dismiss);
  }, [active, chooser, opener]);
  const choose = (panel: MapPanel, button?: HTMLButtonElement) => {
    if (button) setOpener(button);
    if (active !== panel.props.label) panel.props.onOpen?.();
    select(active === panel.props.label && !collapsed && !chooser ? null : panel.props.label);
  };
  const panelButton = (panel: MapPanel) => {
    const { props } = panel;
    return (
      <MapControlLabel key={props.label} label={props.label}>
        <button
          type="button"
          className={`map-icon-button ${toolCaption(props) ? 'map-style-button' : ''}`}
          aria-label={props.label}
          title={props.label}
          aria-expanded={active === props.label && !collapsed && !chooser}
          aria-controls={active === props.label ? id : undefined}
          data-on={props.on ? 'true' : undefined}
          data-active={active === props.label ? 'true' : undefined}
          onClick={(event) => choose(panel, event.currentTarget)}
        >
          <MapControlIcon name={props.icon} />
          {toolCaption(props) && <span className="map-style-label">{toolCaption(props)}</span>}
        </button>
      </MapControlLabel>
    );
  };
  return (
    <>
      <div className="map-layer-rail" role="group" aria-label="Map layers">
        {panels
          .filter(({ props }) => props.entry !== false && props.side === 'left')
          .map(panelButton)}
        <div className="map-rail-divider" />
        {typeof layers === 'function' ? layers(openPanel, active) : layers}
      </div>
      <div className="map-tool-rail" role="group" aria-label="Map tools">
        <MapControlLabel label="Tools">
          <button
            ref={toolsButton}
            type="button"
            className="map-icon-button map-style-button"
            aria-label="Tools"
            aria-expanded={chooser}
            aria-controls={chooser ? `${id}-chooser` : undefined}
            onClick={() => setState((current) => ({ ...current, chooser: !current.chooser }))}
          >
            <MapControlIcon name="settings" />
            <span className="map-style-label">Tools</span>
          </button>
        </MapControlLabel>
        <div className="map-rail-divider" />
        {right.filter(({ props }) => favourites.includes(toolId(props))).map(panelButton)}
      </div>
      {navigation && <div className="map-navigation-rail">{navigation}</div>}
      {activity && (
        <div className="map-active-mode" role="group" aria-label="Active map operation">
          {activity}
        </div>
      )}
      {selected && (
        <MapToolInspector
          id={id}
          label={selected.props.label}
          title={selected.props.title ?? selected.props.label}
          icon={selected.props.icon}
          side={selected.props.side ?? 'right'}
          collapsed={collapsed}
          hidden={chooser}
          closeRef={closeButton}
          onClose={close}
          onCollapse={() => setState((current) => ({ ...current, collapsed: !current.collapsed }))}
          contentKey={selected.props.label}
        >
          {selected.props.children}
        </MapToolInspector>
      )}
      {chooser && (
        <MapToolInspector
          id={`${id}-chooser`}
          label="Tools"
          icon="settings"
          closeRef={chooserClose}
          closeLabel="Close tools"
          onClose={dismissChooser}
        >
          <MapToolChooser
            panels={right}
            favourites={favourites}
            onChoose={(panel) => {
              setOpener(toolsButton.current);
              choose(panel);
            }}
            onPin={(pin) => {
              const next = favourites.includes(pin)
                ? favourites.filter((item) => item !== pin)
                : [...favourites, pin].slice(0, 4);
              setPins(next);
              writeToolFavourites(next);
            }}
          />
        </MapToolInspector>
      )}
    </>
  );
}
