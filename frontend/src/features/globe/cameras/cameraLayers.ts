import { IconLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import type { Camera } from '@/lib/api/cameras';
import type { MapBounds } from '@/lib/map/MapEngine';
import { clusterCameras, type CameraCluster } from './cameraClusters';
import { clusterRadius } from '../layers/clusters';

const ICON = `data:image/svg+xml;utf8,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><g fill="none" stroke="white" stroke-width="5" stroke-linejoin="round"><path d="m8 15 34-6 12 24-34 7zM25 40v11H9M8 44v14M43 15l10-2 6 13-7 3"/><circle cx="39" cy="25" r="5"/></g></svg>')}`;
const GLOBE_WINDING: NonNullable<Layer['props']['parameters']> & Record<number, number> = {
  2886: 2304,
};

/** Public facilities are separate from the timestamped event store. */
export function buildCameraLayers(
  cameras: readonly Camera[],
  onSelect: (camera: Camera) => void,
  selectedId: string | null,
  globe = false,
  zoom = 13,
  onCluster?: (cluster: CameraCluster) => void,
  bounds: MapBounds | null = null,
): Layer[] {
  if (!cameras.length) return [];
  const { loose, clusters } = clusterCameras(cameras, zoom, selectedId, bounds);
  const layers: Layer[] = [
    new IconLayer<Camera>({
      id: 'public-camera-icons',
      data: loose,
      pickable: true,
      billboard: !globe,
      ...(globe ? { parameters: GLOBE_WINDING } : {}),
      getPosition: (camera) => [camera.longitude, camera.latitude],
      getIcon: () => ({ url: ICON, width: 64, height: 64, mask: true }),
      sizeUnits: 'pixels',
      getSize: (camera) => (camera.id === selectedId ? 30 : 22),
      getColor: [98, 222, 190, 240],
      getAngle: globe ? 180 : 0,
      updateTriggers: { getSize: [selectedId] },
      onClick: (info: PickingInfo<Camera>) => {
        if (info.object) onSelect(info.object);
        return true;
      },
    }),
  ];
  if (clusters.length)
    layers.push(
      new ScatterplotLayer<CameraCluster>({
        id: 'public-camera-clusters',
        data: clusters,
        pickable: true,
        radiusUnits: 'pixels',
        stroked: true,
        lineWidthUnits: 'pixels',
        getLineWidth: 1,
        getPosition: (cluster) => [cluster.longitude, cluster.latitude],
        getRadius: (cluster) => clusterRadius(cluster.count),
        getFillColor: [18, 78, 65, 230],
        getLineColor: [98, 222, 190, 255],
        onClick: (info: PickingInfo<CameraCluster>) => {
          if (info.object) onCluster?.(info.object);
          return true;
        },
      }),
      new TextLayer<CameraCluster>({
        id: 'public-camera-cluster-counts',
        data: clusters,
        pickable: false,
        billboard: !globe,
        ...(globe ? { parameters: GLOBE_WINDING } : {}),
        getPosition: (cluster) => [cluster.longitude, cluster.latitude],
        getText: (cluster) => String(cluster.count),
        getSize: 12,
        getColor: [235, 255, 246, 255],
        getTextAnchor: 'middle',
        getAlignmentBaseline: 'center',
        getAngle: globe ? 180 : 0,
      }),
    );
  const selected = cameras.find((camera) => camera.id === selectedId);
  if (selected)
    layers.push(
      new ScatterplotLayer<Camera>({
        id: 'selected-camera-halo',
        data: [selected],
        pickable: false,
        filled: false,
        stroked: true,
        radiusUnits: 'pixels',
        lineWidthUnits: 'pixels',
        getRadius: 21,
        getLineWidth: 3,
        getLineColor: [255, 255, 255, 255],
        getPosition: (camera) => [camera.longitude, camera.latitude],
      }),
    );
  return layers;
}
