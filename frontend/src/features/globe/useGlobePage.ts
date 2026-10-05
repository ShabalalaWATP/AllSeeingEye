/**
 * Composes the live map from responsibility-owned hooks. Every hook is called unconditionally
 * in a fixed order; state stays with the hook that owns it and flows down explicitly.
 */
import { useNow } from '@/lib/hooks/useNow';
import { useGlobeAssistant } from './useGlobeAssistant';
import type { GlobeCanvas, GlobeDisplay } from './useGlobeCanvas';
import { useGlobeCatalogueLayers } from './useGlobeCatalogueLayers';
import { useGlobeEvents } from './useGlobeEvents';
import { useGlobeInterference } from './useGlobeInterference';
import { useGlobeLiveViews } from './useGlobeLiveViews';
import { useGlobeScene } from './useGlobeScene';
import { useGlobeSelection } from './useGlobeSelection';
import { useGlobeSources } from './useGlobeSources';
import { useTechnologyControl } from './useTechnologyControl';

export interface GlobePageInputs {
  display: GlobeDisplay;
  canvas: GlobeCanvas;
  visible: boolean;
  reducedMotion: boolean;
}

/** The single event pipeline consumes the shell's current engine and display inputs. */
export function useGlobePage({ display, canvas, visible, reducedMotion }: GlobePageInputs) {
  const now = useNow();
  const interference = useGlobeInterference(display.interference && visible, now);
  const { engine, supported, tools, symbolMode } = canvas;
  const { countryByIso } = canvas.reference;
  const data = useGlobeEvents(now);
  const liveViews = useGlobeLiveViews(engine, display, data, interference.filters);
  const scope = { data, countryByIso, engine, picking: tools.picking, symbolMode, now };
  const sources = useGlobeSources({ ...scope, supported, visible });
  const selection = useGlobeSelection({ ...scope, sources });
  const catalogue = useGlobeCatalogueLayers({
    ...scope,
    sources,
    selection,
    gridLayers: canvas.britishGrid.layers,
    toolLayers: canvas.toolLayers,
  });
  const technology = useTechnologyControl(
    sources.network,
    sources.infrastructure,
    data.country,
    catalogue.networkSelection.selectRecord,
  );
  useGlobeAssistant({
    engine,
    supported,
    inspected: data.selected ?? sources.context.event,
    sources,
    selection,
    catalogue,
  });
  const { details } = selection;
  useGlobeScene({
    engine,
    events: data.quality.filtered,
    hidden: data.renderHidden,
    selectedId: data.selectedId,
    highlightedId: selection.highlightedId,
    onPick: selection.onPick,
    onCluster: selection.onCluster,
    onJam: selection.onJam,
    jamCells: interference.filters.filtered,
    jamSelection: details?.kind === 'jam' ? details.cell : null,
    layerGroups: catalogue.layerGroups,
    supported,
    terminator: display.terminator,
    lite: display.lite,
    interference: display.interference,
    // A rotating playlist holds each saved view's camera instead of turning the globe.
    opsRoom: display.opsRoom && !liveViews.rotating,
    reducedMotion,
    visible,
    now,
    zoom: canvas.zoom,
    mode: display.mode,
    symbolMode,
  });

  const { country } = data;
  return {
    display,
    canvas: {
      containerRef: canvas.containerRef,
      supported,
      engine,
      britishGrid: canvas.britishGrid,
      tools,
      savedArea: canvas.savedArea,
    },
    reference: {
      ...canvas.reference,
      changeNation: selection.changeNation,
      nation: country === null ? null : (countryByIso[country] ?? null),
    },
    events: {
      data,
      hidden: data.hidden,
      country,
      selectedId: data.selectedId,
      selected: data.selected,
      quality: data.quality,
      storySize: data.storySize,
      details,
      pickableEvents: selection.pickableEvents,
      choose: selection.choose,
      close: selection.close,
      onJam: selection.onJam,
      focus: selection.focus,
      selectTraffic: selection.selectTraffic,
    },
    sources: { ...sources, gnss: interference.gnss, gnssFilters: interference.filters },
    actions: {
      technology,
      selectContext: selection.selectContext,
      selectSatellite: selection.selectSatellite,
      focusInfrastructure: catalogue.focusInfrastructure,
      focusCamera: catalogue.focusCamera,
      focusFigure: catalogue.focusFigure,
      regionSelection: catalogue.regionSelection,
      cyberSelection: catalogue.cyberSelection,
      networkSelection: catalogue.networkSelection,
    },
    liveViews,
    now,
  };
}

export type GlobePageModel = ReturnType<typeof useGlobePage>;
