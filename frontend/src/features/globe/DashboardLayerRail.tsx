import type { ComponentProps } from 'react';
import { MapLayerRail } from './MapLayerRail';
import type { useDashboardEvents } from './useDashboardEvents';

/** Adapt the shared event pipeline to the layer rail without duplicating filter state. */
export function DashboardLayerRail({
  data,
  cyberCount,
  ...controls
}: Pick<
  ComponentProps<typeof MapLayerRail>,
  'openPanel' | 'activePanel' | 'onTrafficSelect' | 'selectionDisabled'
> & { data: ReturnType<typeof useDashboardEvents>; cyberCount: number }) {
  const { observations } = data;
  return (
    <MapLayerRail
      {...controls}
      events={data.scoped}
      counts={{ ...data.counts, cyber: cyberCount }}
      fires={data.fires}
      news={data.news}
      visibility={observations.visibility}
      onToggle={observations.toggle}
      flightFilter={observations.flightFilter}
      onFlightFilter={observations.setFlightFilter}
      vesselFilter={observations.vesselFilter}
      onVesselFilter={observations.setVesselFilter}
    />
  );
}
