export type ScenePair = [number, number];
export interface GeneratedSceneLayer {
  id: string;
  kind: 'points' | 'routes' | 'orbits' | 'cells' | 'zones';
  points: ScenePair[];
  routes: ScenePair[][];
  steps: number;
}
export interface GeneratedScene {
  seed: number;
  layers: GeneratedSceneLayer[];
}
export const SCENE_SEED: number;
export function seededRandom(seed: number): () => number;
export function buildProductScene(maskBase64: string): GeneratedScene;
export function serialiseScene(scene: GeneratedScene): string;
export function readLandMask(source?: string): string;
