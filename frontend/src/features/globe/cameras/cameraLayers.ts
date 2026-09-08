import { IconLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import type { Camera } from '@/lib/api/cameras';

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
): Layer[] {
  if (!cameras.length) return [];
  const layers: Layer[] = [
    new IconLayer<Camera>({
      id: 'public-camera-icons',
      data: cameras,
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
