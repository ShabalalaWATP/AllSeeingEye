import { useId, useState } from 'react';
import { MapControlIcon } from './MapControlIcon';
import { TOOL_GROUPS, toolDescription, toolGroup, toolId } from './mapToolDefinitions';
import type { MapPanel } from './mapToolDefinitions';

export function MapToolChooser({
  panels,
  favourites,
  onPin,
  onChoose,
}: {
  panels: MapPanel[];
  favourites: string[];
  onPin: (id: string) => void;
  onChoose: (panel: MapPanel) => void;
}) {
  const [query, setQuery] = useState('');
  const id = useId();
  const matching = panels.filter(({ props }) =>
    `${props.label} ${props.title ?? ''} ${toolDescription(props)} ${toolGroup(props)}`
      .toLowerCase()
      .includes(query.trim().toLowerCase()),
  );
  return (
    <div className="map-tool-chooser">
      <label htmlFor={id}>Find a tool</label>
      <input
        id={id}
        type="search"
        value={query}
        placeholder="Search tools"
        onChange={(event) => setQuery(event.target.value)}
      />
      <p className="map-tool-chooser-hint">Pin up to four tools for quick access.</p>
      {matching.length === 0 && <p role="status">No tools match this search.</p>}
      {TOOL_GROUPS.map((group) => {
        const entries = matching.filter(({ props }) => toolGroup(props) === group);
        return (
          entries.length > 0 && (
            <section key={group} aria-label={group}>
              <h3>{group}</h3>
              {entries.map((panel) => {
                const pinned = favourites.includes(toolId(panel.props));
                return (
                  <div className="map-tool-choice" key={panel.props.label}>
                    <button
                      type="button"
                      aria-label={panel.props.label}
                      aria-describedby={`${id}-${encodeURIComponent(toolId(panel.props))}`}
                      onClick={() => onChoose(panel)}
                    >
                      <MapControlIcon name={panel.props.icon} />
                      <span>
                        <strong>{panel.props.title ?? panel.props.label}</strong>
                        <small id={`${id}-${encodeURIComponent(toolId(panel.props))}`}>
                          {toolDescription(panel.props)}
                        </small>
                      </span>
                    </button>
                    <button
                      type="button"
                      className="map-tool-pin"
                      aria-label={`${pinned ? 'Unpin' : 'Pin'} ${panel.props.label}`}
                      aria-pressed={pinned}
                      disabled={!pinned && favourites.length >= 4}
                      onClick={() => onPin(toolId(panel.props))}
                    >
                      <span aria-hidden="true">{pinned ? '★' : '☆'}</span>
                    </button>
                  </div>
                );
              })}
            </section>
          )
        );
      })}
    </div>
  );
}
