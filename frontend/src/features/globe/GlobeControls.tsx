import { Children, isValidElement, useCallback, useEffect, useId, useRef, useState } from 'react';
import type { ReactNode, RefObject } from 'react';
import { resolveMapPanel } from '@/lib/mapLayerDirectory';
import { MapControlLabel } from './MapControlLabel';
import { MapControlIcon } from './MapControlIcon';
import { MapToolChooser } from './MapToolChooser';
import { MapToolInspector } from './MapToolInspector';
import { MapToolButton } from './MapToolButton';
import { DEFAULT_FAVOURITES, toolCaption, toolId } from './mapToolDefinitions';
import type { MapPanel, PanelProps } from './mapToolDefinitions';
import { readToolFavourites, writeToolFavourites } from './mapToolPreferences';
import './mapToolShell.css';

export function ControlPanel({ children }: PanelProps) {
  return typeof children === 'function' ? children() : children;
}
/** Non-modal tools leave map gestures available, including while measuring. */
export type OpenPanel = (label: string, button?: HTMLButtonElement | null) => void;
/**
 * Opens a panel from a control outside the rails without toggling it closed, moves focus to
 * the first element matching `focus` inside it, and returns focus to `opener` on close.
 */
export type ShowPanel = (label: string, opener: HTMLElement, focus: string) => void;

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
  showRef,
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
  /** Receives a handle that opens a panel from outside the rails, such as a skip link. */
  showRef?: RefObject<ShowPanel | null>;
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
  const [opener, setOpener] = useState<HTMLElement | null>(null);
  // A direct entry names what to focus inside the panel; the tick re-runs focus when the
  // panel was already open.
  const entryFocus = useRef<string | null>(null);
  const [entryTick, setEntryTick] = useState(0);
  const closeButton = useRef<HTMLButtonElement>(null);
  const chooserClose = useRef<HTMLButtonElement>(null);
  const toolsButton = useRef<HTMLButtonElement>(null);
  const [pins, setPins] = useState(readToolFavourites);
  const select = useCallback(
    (label: string | null) => {
      setState((current) => ({ ...current, active: label, collapsed: false, chooser: false }));
      onPanelChange?.(label);
    },
    [onPanelChange],
  );
  const openPanel: OpenPanel = useCallback(
    (label, button) => {
      if (button) setOpener(button);
      select(active === label && !collapsed ? null : label);
    },
    [active, collapsed, select],
  );
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
    if (!showRef) return;
    showRef.current = (label, from, focus) => {
      setOpener(from);
      entryFocus.current = focus;
      setEntryTick((tick) => tick + 1);
      setState((current) => ({ ...current, active: label, collapsed: false, chooser: false }));
      navigated.current?.(label);
    };
    return () => {
      showRef.current = null;
    };
  }, [showRef]);
  useEffect(() => {
    if (!active) return;
    const focus = entryFocus.current;
    entryFocus.current = null;
    const inspector = document.getElementById(id);
    const target = focus ? inspector?.querySelector<HTMLElement>(focus) : null;
    if (target) target.focus();
    // The address echo of an open panel must not pull focus back out of its content.
    else if (!inspector?.contains(document.activeElement)) closeButton.current?.focus();
  }, [active, opener, requestKey, entryTick, id]);
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
  const choose = useCallback(
    (label: string, onOpen: (() => void) | undefined, button?: HTMLButtonElement) => {
      if (button) setOpener(button);
      if (active !== label) onOpen?.();
      select(active === label && !collapsed && !chooser ? null : label);
    },
    [active, collapsed, chooser, select],
  );
  const panelButton = (panel: MapPanel) => {
    const { props } = panel;
    return (
      <MapToolButton
        key={props.label}
        label={props.label}
        icon={props.icon}
        caption={toolCaption(props)}
        on={props.on}
        active={active === props.label}
        expanded={active === props.label && !collapsed && !chooser}
        controls={active === props.label ? id : undefined}
        onOpen={props.onOpen}
        onChoose={choose}
      />
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
          {typeof selected.props.children === 'function'
            ? selected.props.children()
            : selected.props.children}
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
              choose(panel.props.label, panel.props.onOpen);
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
