import { useCallback } from 'react';
import type { AssistantMapTarget } from '@/lib/assistantMapContext';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { CameraState } from './cameras/useCameras';
import type {
  InfrastructureSelection,
  InfrastructureState,
} from './infrastructure/useInfrastructure';

/** Only select records that are actually present in a currently visible map layer. */
export function useAssistantMapSelection(
  events: readonly LiveEvent[],
  cameras: CameraState,
  infrastructure: InfrastructureState,
  chooseEvent: (event: LiveEvent) => void,
  focusCamera: (camera: CameraState['visible'][number]) => void,
  focusInfrastructure: (selection: InfrastructureSelection) => void,
) {
  const {
    data,
    cablesEnabled,
    stationsEnabled,
    nuclearEnabled,
    dataCentresEnabled,
    energyEnabled,
    semiconductorEnabled,
  } = infrastructure;
  const cameraRows = cameras.visible;
  return useCallback(
    (target: AssistantMapTarget): boolean => {
      if (target.kind === 'event') {
        const event = events.find((item) => item.id === target.id);
        if (!event) return false;
        chooseEvent(event);
        return true;
      }
      if (target.kind === 'camera') {
        const camera = cameraRows.find((item) => item.id === target.id);
        if (!camera) return false;
        focusCamera(camera);
        return true;
      }
      if (target.kind !== 'infrastructure' || !data) return false;
      const cable = cablesEnabled && data.cables.find((row) => row.id === target.id);
      const station = stationsEnabled && data.ground_stations.find((row) => row.id === target.id);
      const nuclear = nuclearEnabled && data.nuclear_facilities.find((row) => row.id === target.id);
      const centre = dataCentresEnabled && data.data_centres.find((row) => row.id === target.id);
      const energy = energyEnabled && data.energy_sites.find((row) => row.id === target.id);
      const chip =
        semiconductorEnabled && data.semiconductor_sites.find((row) => row.id === target.id);
      const selection: InfrastructureSelection | null = cable
        ? { kind: 'cable', item: cable }
        : station
          ? { kind: 'station', item: station }
          : nuclear
            ? { kind: 'nuclear', item: nuclear }
            : centre
              ? { kind: 'data_centre', item: centre }
              : energy
                ? { kind: 'energy_site', item: energy }
                : chip
                  ? { kind: 'semiconductor_site', item: chip }
                  : null;
      if (selection) {
        focusInfrastructure(selection);
        return true;
      }
      return false;
    },
    [
      events,
      cameraRows,
      data,
      cablesEnabled,
      stationsEnabled,
      nuclearEnabled,
      dataCentresEnabled,
      energyEnabled,
      semiconductorEnabled,
      chooseEvent,
      focusCamera,
      focusInfrastructure,
    ],
  );
}
