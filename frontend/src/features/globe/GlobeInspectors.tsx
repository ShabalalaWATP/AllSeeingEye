import type { ComponentProps } from 'react';
import { ConflictRegionInspector } from './ConflictRegionInspector';
import { InfrastructureInspector } from './infrastructure/InfrastructureInspector';
import { CameraInspector } from './cameras/CameraInspector';
import { SelectedMapDetails } from './SelectedMapDetails';
import type { useConflictRegions } from './useConflictRegions';
import type { useInfrastructure } from './infrastructure/useInfrastructure';
import type { useCameras } from './cameras/useCameras';

/** A single inspector slot for every map selection. */
export function GlobeInspectors({
  regions,
  infrastructure,
  cameras,
  eventDetails,
}: {
  regions: ReturnType<typeof useConflictRegions>;
  infrastructure: ReturnType<typeof useInfrastructure>;
  cameras: ReturnType<typeof useCameras>;
  eventDetails: ComponentProps<typeof SelectedMapDetails>;
}) {
  if (regions.selected)
    return <ConflictRegionInspector region={regions.selected} onClose={regions.close} />;
  if (infrastructure.selected)
    return (
      <InfrastructureInspector
        selected={infrastructure.selected}
        data={infrastructure.data}
        onClose={infrastructure.close}
      />
    );
  if (cameras.selected)
    return (
      <CameraInspector
        key={cameras.selected.id}
        camera={cameras.selected}
        onClose={cameras.close}
      />
    );
  return <SelectedMapDetails {...eventDetails} />;
}
