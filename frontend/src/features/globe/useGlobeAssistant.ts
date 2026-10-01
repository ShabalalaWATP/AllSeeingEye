/** Shares the inspected map record with the Eye assistant and lets it select visible records. */
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { GlobeCatalogueLayers } from './useGlobeCatalogueLayers';
import type { GlobeEngineHandle } from './useGlobeEngine';
import type { GlobeSelection } from './useGlobeSelection';
import type { GlobeSources } from './useGlobeSources';
import { useAssistantMapSelection } from './useAssistantMapSelection';
import { useEyeMapContext } from './useEyeMapContext';

export function useGlobeAssistant({
  engine,
  supported,
  inspected,
  sources: { cameras, infrastructure },
  selection: { pickableEvents, choose },
  catalogue: { focusCamera, focusInfrastructure },
}: {
  engine: GlobeEngineHandle;
  supported: boolean;
  /** The selected live event, else the selected context record. */
  inspected: LiveEvent | null;
  sources: Pick<GlobeSources, 'cameras' | 'infrastructure'>;
  selection: Pick<GlobeSelection, 'pickableEvents' | 'choose'>;
  catalogue: Pick<GlobeCatalogueLayers, 'focusCamera' | 'focusInfrastructure'>;
}): void {
  const selectSource = useAssistantMapSelection(
    pickableEvents,
    cameras,
    infrastructure,
    choose,
    focusCamera,
    focusInfrastructure,
  );
  useEyeMapContext(engine, supported, inspected, cameras, infrastructure, selectSource);
}
