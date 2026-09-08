import { BritishGridPanel } from './BritishGridPanel';
import type { useBritishGrid } from './useBritishGrid';
import type { GlobeEngineHandle } from './useGlobeEngine';

export function BritishGridTool({
  grid,
  engine,
}: {
  grid: ReturnType<typeof useBritishGrid>;
  engine: GlobeEngineHandle;
}) {
  return (
    <BritishGridPanel
      enabled={grid.enabled}
      onToggle={() => grid.setEnabled(!grid.enabled)}
      onLocate={() => {
        grid.setEnabled(true);
        engine.flyTo({ center: [-2.5, 55], zoom: 5.5 });
      }}
      zoom={grid.zoom}
    />
  );
}
