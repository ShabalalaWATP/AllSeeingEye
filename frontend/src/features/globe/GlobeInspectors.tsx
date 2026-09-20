import type { ComponentProps } from 'react';
import { ConflictRegionInspector } from './ConflictRegionInspector';
import { CyberCountryInspector } from './CyberCountryInspector';
import { NewsCountryInspector } from './NewsCountryInspector';
import type { useNewsCountryContext } from './useNewsCountryContext';
import { InfrastructureInspector } from './infrastructure/InfrastructureInspector';
import { CameraInspector } from './cameras/CameraInspector';
import { FigureInspector } from './figures/FigureInspector';
import type { useFigures } from './figures/useFigures';
import { SelectedMapDetails } from './SelectedMapDetails';
import type { useConflictRegions } from './useConflictRegions';
import type { useInfrastructure } from './infrastructure/useInfrastructure';
import type { useCameras } from './cameras/useCameras';
import type { useCyberCountryContext } from './useCyberCountryContext';
import { NetworkCountryInspector } from './NetworkCountryInspector';
import type { NetworkCountryGroup } from './networkContext';
import { RadarAttackInspector } from './RadarAttackInspector';
import type { useRadarAttackMap } from './useRadarAttackMap';

/** A single inspector slot for every map selection. */
export function GlobeInspectors({
  regions,
  infrastructure,
  cameras,
  figures,
  eventDetails,
  cyber,
  news,
  network,
  radar,
}: {
  regions: ReturnType<typeof useConflictRegions>;
  infrastructure: ReturnType<typeof useInfrastructure>;
  cameras: ReturnType<typeof useCameras>;
  figures?: ReturnType<typeof useFigures>;
  eventDetails: ComponentProps<typeof SelectedMapDetails>;
  cyber?: {
    state: ReturnType<typeof useCyberCountryContext>;
    onSelect: ComponentProps<typeof CyberCountryInspector>['onSelect'];
  };
  news?: {
    state: ReturnType<typeof useNewsCountryContext>;
    onSelect: ComponentProps<typeof NewsCountryInspector>['onSelect'];
  };
  network?: { selected: NetworkCountryGroup | null; onClose: () => void };
  radar?: ReturnType<typeof useRadarAttackMap>;
}) {
  if (radar?.selected && radar.data)
    return (
      <RadarAttackInspector row={radar.selected} snapshot={radar.data} onClose={radar.close} />
    );
  if (network?.selected)
    return <NetworkCountryInspector group={network.selected} onClose={network.onClose} />;
  if (news?.state.selected)
    return (
      <NewsCountryInspector
        group={news.state.selected}
        onClose={news.state.close}
        onSelect={news.onSelect}
      />
    );
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
  if (figures?.selected)
    return (
      <FigureInspector
        figure={figures.selected}
        onClose={figures.close}
        visibleFigures={figures.visible}
        onSelectFigure={figures.select}
      />
    );
  return <SelectedMapDetails {...eventDetails} />;
}
