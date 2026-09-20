import type { Layer } from '@deck.gl/core';
import { PathLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { TerrainStudy, TerrainStudySample } from './terrainAnalysis';

const COLOURS: Record<TerrainStudySample['visibility'], [number, number, number, number]> = {
  observer: [255, 255, 255, 255],
  visible: [65, 214, 160, 240],
  hidden: [245, 132, 93, 240],
  unknown: [155, 163, 178, 210],
};

/** No filled viewshed: unsampled spaces are deliberately left uncoloured. */
export function terrainAnalysisLayers(
  study: TerrainStudy | null,
  flat: boolean,
  highlighted = -1,
): Layer[] {
  if (!study) return [];
  const samples = study.samples.filter(
    (sample) => !flat || Math.abs(sample.position[1]) <= 85.05112878,
  );
  const layers: Layer[] = [];
  if (study.input.mode === 'profile') {
    // Split at the antimeridian so a flat map never joins across its whole width.
    const paths: TerrainStudySample[][] = [[]];
    for (const sample of samples) {
      const previous = paths.at(-1)?.at(-1);
      if (previous && Math.abs(previous.position[0] - sample.position[0]) > 180) paths.push([]);
      paths.at(-1)?.push(sample);
    }
    layers.push(
      new PathLayer({
        id: 'terrain-study-profile',
        data: paths.filter((path) => path.length > 1),
        getPath: (path: TerrainStudySample[]) => path.map((sample) => sample.position),
        getColor: [108, 203, 255, 230],
        getWidth: 3,
        widthUnits: 'pixels',
        pickable: false,
      }),
    );
  }
  layers.push(
    new ScatterplotLayer<TerrainStudySample>({
      id: 'terrain-study-samples',
      data: samples,
      getPosition: (sample) => sample.position,
      getFillColor: (sample) => COLOURS[sample.visibility],
      getRadius: 3,
      radiusUnits: 'pixels',
      pickable: false,
    }),
  );
  const selected = study.samples[highlighted];
  if (selected)
    layers.push(
      new ScatterplotLayer<TerrainStudySample>({
        id: 'terrain-study-highlight',
        data: [selected],
        getPosition: (sample) => sample.position,
        getFillColor: [255, 221, 100, 255],
        getRadius: 7,
        radiusUnits: 'pixels',
        pickable: false,
      }),
    );
  return layers;
}
