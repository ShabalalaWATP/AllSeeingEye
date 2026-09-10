import { BNG_MIN_ZOOM, BNG_NOTE } from '@/lib/map/britishGrid';
import { MapToolIntro } from '@/components/maps/MapToolIntro';
import './referenceTools.css';

export function BritishGridPanel({
  enabled,
  onToggle,
  onLocate,
  zoom,
}: {
  enabled: boolean;
  onToggle: () => void;
  onLocate: () => void;
  zoom: number;
}) {
  return (
    <div className="map-tool-workspace">
      <MapToolIntro
        title="British National Grid"
        description="Read approximate eastings and northings across Great Britain."
        status={enabled ? 'Grid enabled' : 'Grid off'}
        statusActive={enabled}
      />
      <label className="map-reference-switch">
        <span>
          <span className="map-reference-switch-title">Show British National Grid</span>
          <span className="map-tool-help">100 km lines, with 10 km detail when zoomed in.</span>
        </span>
        <input
          type="checkbox"
          aria-label="Show British National Grid"
          className="map-reference-checkbox"
          checked={enabled}
          onChange={onToggle}
        />
      </label>
      {enabled && zoom < BNG_MIN_ZOOM && (
        <p role="status" className="map-tool-notice">
          Zoom in to see the grid, or locate Great Britain below.
        </p>
      )}
      <section className="map-tool-section">
        <h3 className="map-tool-section-title">Read a grid reference</h3>
        <p className="map-tool-help">
          Move the pointer over Great Britain or the surrounding grid extent. Coordinates appear at
          the bottom of the map.
        </p>
        <button type="button" onClick={onLocate} className="map-tool-primary">
          Locate Great Britain
        </button>
      </section>
      <p className="map-tool-help map-reference-footnote">{BNG_NOTE}</p>
    </div>
  );
}
