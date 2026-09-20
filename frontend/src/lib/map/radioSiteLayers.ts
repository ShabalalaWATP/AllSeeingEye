import { ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Position } from './geoJsonTypes';
import type { RfSiteNames } from './rfSites';
import { rfReferenceVisible } from './rfReferenceGeometry';

interface RadioSiteMarker {
  point: Position;
  label: string;
}

/** Sites remain visible while inputs change and before an analysis has run. */
export function radioSiteLayers(
  origin: Position | null,
  receiver: Position | null,
  names: RfSiteNames,
  flat: boolean,
) {
  const sites = [
    ...(origin ? [{ point: origin, label: `TX${names.origin ? ` · ${names.origin}` : ''}` }] : []),
    ...(receiver
      ? [{ point: receiver, label: `RX${names.receiver ? ` · ${names.receiver}` : ''}` }]
      : []),
  ].filter(({ point }) => rfReferenceVisible(point, flat));
  if (!sites.length) return [];
  return [
    new ScatterplotLayer<RadioSiteMarker>({
      id: 'radio-workspace-sites',
      data: sites,
      getPosition: (site) => site.point,
      getRadius: 8,
      radiusUnits: 'pixels',
      getFillColor: [121, 216, 235, 255],
      stroked: true,
      getLineColor: [4, 10, 16, 255],
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      pickable: false,
      wrapLongitude: flat,
    }),
    new TextLayer<RadioSiteMarker>({
      id: 'radio-workspace-site-labels',
      data: sites,
      getPosition: (site) => site.point,
      getText: (site) => site.label,
      getSize: 12,
      getColor: [245, 251, 255, 255],
      getPixelOffset: [0, 22],
      background: true,
      backgroundPadding: [6, 4],
      getBackgroundColor: [4, 10, 16, 235],
      pickable: false,
      wrapLongitude: flat,
    }),
  ];
}
