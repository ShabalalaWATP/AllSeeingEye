import type { ComponentProps } from 'react';
import { ConflictRegionInspector } from './ConflictRegionInspector';
import { CyberCountryInspector } from './CyberCountryInspector';
import { InfrastructureInspector } from './infrastructure/InfrastructureInspector';
import { CameraInspector } from './cameras/CameraInspector';
import { SelectedMapDetails } from './SelectedMapDetails';
import type { useConflictRegions } from './useConflictRegions';
import type { useInfrastructure } from './infrastructure/useInfrastructure';
import type { useCameras } from './cameras/useCameras';
import type { useCyberCountryContext } from './useCyberCountryContext';

/** A single inspector slot for every map selection. */
export function GlobeInspectors({
  regions,
  infrastructure,
  cameras,
  eventDetails,
  cyber,
}: {
  regions: ReturnType<typeof useConflictRegions>;
  infrastructure: ReturnType<typeof useInfrastructure>;
  cameras: ReturnType<typeof useCameras>;
  eventDetails: ComponentProps<typeof SelectedMapDetails>;
  cyber?: {
    state: ReturnType<typeof useCyberCountryContext>;
    onSelect: ComponentProps<typeof CyberCountryInspector>['onSelect'];
  };
}) {
  if (cyber?.state.selected)
    return (
      <CyberCountryInspector
        group={cyber.state.selected}
        onClose={cyber.state.close}
        onSelect={cyber.onSelect}
      />
    );
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
