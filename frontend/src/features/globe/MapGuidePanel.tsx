import { Link } from 'react-router';

import { MapToolIntro } from '@/components/maps/MapToolIntro';
import {
  MAP_GUIDE_PANEL,
  MAP_LAYER_GROUPS,
  type MapLayerEntry,
  type MapLayerToggle,
} from '@/lib/mapLayerDirectory';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';

import { ControlPanel, type OpenPanel } from './GlobeControls';
import { toggleObservationLayer } from './layerVisibility';
import type { MapGuideSources } from './mapGuideControls';
import { guideSwitches } from './mapGuideControls';

function GuideRow({
  entry,
  state,
  open,
}: {
  entry: MapLayerEntry;
  state: { on: boolean; set: () => void } | undefined;
  open: OpenPanel;
}) {
  const panel = entry.panel;
  return (
    <li className="flex flex-col gap-1 border-t border-line/70 py-2 first:border-t-0">
      <div className="flex items-start gap-2">
        <span className="min-w-0 flex-1 text-[13px] font-medium">{entry.label}</span>
        {state && (
          <button
            type="button"
            role="switch"
            aria-checked={state.on}
            aria-label={`${entry.label} on the map`}
            onClick={state.set}
            className="map-tool-text-button shrink-0 px-2"
          >
            <span className="map-tool-switch-track" aria-hidden="true" />
          </button>
        )}
      </div>
      <p className="text-[11px] leading-relaxed text-muted">{entry.description}</p>
      {panel !== undefined && (
        <button
          type="button"
          className="map-tool-text-button self-start px-2"
          onClick={() => {
            open(panel);
          }}
        >
          Open {panel}
        </button>
      )}
    </li>
  );
}

/** Names every layer and tool the map offers, says what it is and switches it on. */
export function MapGuide({ open, sources }: { open: OpenPanel; sources: MapGuideSources }) {
  const hidden = useEventsStore((state) => state.hidden);
  const toggleCategory = useEventsStore((state) => state.toggleCategory);
  const interference = useGlobeStore((state) => state.interference);
  const toggleInterference = useGlobeStore((state) => state.toggleInterference);
  const { observations } = sources.events;
  const switches: Partial<Record<MapLayerToggle, { on: boolean; set: () => void }>> = {
    ...guideSwitches(sources, hidden, toggleCategory),
    interference: { on: interference, set: toggleInterference },
    aircraft: {
      on: observations.visibility.aircraft && !hidden.includes('aviation'),
      set: () =>
        toggleObservationLayer(
          'aircraft',
          observations.visibility,
          hidden,
          observations.toggle,
          toggleCategory,
        ),
    },
    vessels: {
      on: observations.visibility.vessels && !hidden.includes('maritime'),
      set: () =>
        toggleObservationLayer(
          'vessels',
          observations.visibility,
          hidden,
          observations.toggle,
          toggleCategory,
        ),
    },
  };
  return (
    <div className="map-tool-workspace">
      <MapToolIntro
        title={MAP_GUIDE_PANEL}
        description="Everything this map can show. Switch a layer on here, or open the tool that holds its filters."
      />
      {MAP_LAYER_GROUPS.map((group) => (
        <section key={group.title} className="map-tool-section">
          <h3 className="map-tool-section-title">{group.title}</h3>
          <ul aria-label={group.title}>
            {group.items.map((entry) => (
              <GuideRow
                key={entry.id}
                entry={entry}
                state={entry.toggle === undefined ? undefined : switches[entry.toggle]}
                open={open}
              />
            ))}
          </ul>
        </section>
      ))}
      <section className="map-tool-section">
        <h3 className="map-tool-section-title">Where the data comes from</h3>
        <p className="text-[11px] leading-relaxed text-muted">
          Every feed, camera index, map layer and dataset behind these layers is listed with its
          current state in the source catalogue.
        </p>
        <Link to="/sources" className="map-tool-text-button self-start px-2">
          Open sources &amp; data
        </Link>
      </section>
    </div>
  );
}

export function mapGuidePanel(open: OpenPanel, sources: MapGuideSources) {
  return (
    <ControlPanel key="guide" side="left" label={MAP_GUIDE_PANEL} icon="guide" caption="Guide">
      <MapGuide open={open} sources={sources} />
    </ControlPanel>
  );
}
