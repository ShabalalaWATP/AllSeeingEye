import { useState } from 'react';
import { researchAreaGeometry } from '@/lib/map/researchAreaGeometry';
import type { WorkspaceOverlay } from './useWorkspaceVisibility';
import type { useMapWorkspaceTools } from './useMapWorkspaceTools';
import type { OpenPanel } from './GlobeControls';

/** A small list of artefacts, independent of the tool that created each one. */
export function MapWorkspacePanel({
  tools,
  open,
}: {
  tools: ReturnType<typeof useMapWorkspaceTools>;
  open: OpenPanel;
}) {
  const [error, setError] = useState<string | null>(null);
  const overlays: {
    id: WorkspaceOverlay;
    name: string;
    panel: string;
    exists: boolean;
    clear: () => void;
  }[] = [
    {
      id: 'sketch',
      name: 'Current sketch',
      panel: 'Draw on map',
      exists: tools.drawing.anchors.length > 0,
      clear: tools.drawing.clear,
    },
    {
      id: 'measurement',
      name: 'Measurement',
      panel: 'Measure distance and area',
      exists: tools.measurement.points.length > 0,
      clear: tools.measurement.clear,
    },
    {
      id: 'research',
      name: 'Research boundary',
      panel: 'Research area',
      exists: tools.research.area !== null || tools.research.drawing.anchors.length > 0,
      clear: tools.research.clear,
    },
    {
      id: 'radio',
      name: 'Radio study',
      panel: 'RF link calculator',
      exists:
        tools.rf.origin !== null ||
        tools.rf.receiver !== null ||
        tools.rf.analysis !== null ||
        tools.rf.estimate !== null,
      clear: tools.rf.clearSites,
    },
    {
      id: 'route',
      name: 'Planned route',
      panel: 'Route planner',
      exists: tools.routePlanner.route !== null,
      clear: () => tools.setRoute(null),
    },
    {
      id: 'terrain',
      name: 'Terrain study',
      panel: 'Terrain profile and visibility',
      exists: tools.terrainStudy.result !== null || tools.terrainStudy.busy,
      clear: tools.terrainStudy.clear,
    },
  ];
  const existing = overlays.filter((item) => item.exists);
  return (
    <section className="map-tool-section" aria-label="Workspace objects">
      <p className="map-tool-help">
        Reopen a tool or hide its result without losing its inputs. Save drawings and radio studies
        in their tools.
      </p>
      {error && (
        <p role="alert" className="map-tool-notice">
          {error}
        </p>
      )}
      {!existing.length && !tools.drawingWorkspace.objects.length && (
        <p className="map-tool-help">Your map has no drawings or analysis results yet.</p>
      )}
      <ul className="divide-y divide-edge" aria-label="Current map results">
        {existing.map((item) => (
          <li key={item.id} className="py-3">
            <label className="flex min-h-11 items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={tools.visible[item.id]}
                onChange={(event) => tools.setVisible(item.id, event.target.checked)}
              />
              {item.name}
            </label>
            <div className="flex gap-4">
              <button
                type="button"
                className="map-tool-text-button"
                onClick={() => open(item.panel)}
              >
                Open {item.name.toLowerCase()}
              </button>
              <button type="button" className="map-tool-text-button" onClick={item.clear}>
                Clear {item.name.toLowerCase()}
              </button>
            </div>
          </li>
        ))}
      </ul>
      {tools.drawingWorkspace.objects.length > 0 && (
        <>
          <h3 className="map-tool-section-title">Drawings</h3>
          <ul className="divide-y divide-edge" aria-label="Workspace drawings">
            {tools.drawingWorkspace.objects.map((item) => (
              <li key={item.id} className="py-3">
                <label className="flex min-h-11 items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={item.visible}
                    onChange={(event) =>
                      tools.drawingWorkspace.updateObject(item.id, {
                        visible: event.target.checked,
                      })
                    }
                  />
                  <span className="break-words">
                    {item.name}
                    {item.locked ? ' · locked' : ''}
                  </span>
                </label>
                <div className="flex flex-wrap gap-x-4">
                  <button
                    type="button"
                    className="map-tool-text-button"
                    onClick={() => {
                      tools.drawingWorkspace.select(item.id);
                      open('Draw on map');
                    }}
                  >
                    Edit
                  </button>
                  {item.shape !== 'point' && item.shape !== 'path' && (
                    <button
                      type="button"
                      className="map-tool-text-button"
                      onClick={() => {
                        try {
                          if (item.shape === 'point') return;
                          tools.adoptResearch(researchAreaGeometry(item.shape, item.anchors));
                          setError(null);
                          open('Research area');
                        } catch (failure) {
                          setError(
                            failure instanceof Error
                              ? failure.message
                              : 'Unable to use this boundary.',
                          );
                        }
                      }}
                    >
                      Research
                    </button>
                  )}
                  {item.shape === 'point' && (
                    <button
                      type="button"
                      className="map-tool-text-button"
                      onClick={() => {
                        const position = item.anchors[0];
                        if (position) {
                          tools.rf.setSite('origin', position, item.name);
                          open('RF link calculator');
                        }
                      }}
                    >
                      Use as transmitter
                    </button>
                  )}
                  <button
                    type="button"
                    className="map-tool-text-button"
                    disabled={item.locked}
                    onClick={() => tools.drawingWorkspace.remove(item.id)}
                  >
                    Remove
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
      <button type="button" className="map-tool-secondary" onClick={() => open('Draw on map')}>
        Draw or open a collection
      </button>
    </section>
  );
}
