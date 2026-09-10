import type { Position } from './geoJsonTypes';
import type { RfEngineeringSettings } from './rfEngineering';

export type RfTerrainStatus = 'clear' | 'risk' | 'blocked' | 'unknown';
export interface RfTerrainSamplePlan {
  kind: 'path' | 'radial';
  origin: Position;
  receiver: Position | null;
  maxDistanceKm: number;
  positions: Position[];
  profiles: { bearingDegrees: number; indices: number[]; distancesM: number[] }[];
}
export interface RfTerrainProfilePoint {
  position: Position;
  distanceM: number;
  elevationM: number | null;
  obstacleHeightM?: number;
  earthBulgeM: number;
  rayHeightM: number | null;
  clearanceM: number | null;
  fresnel60M: number;
  fresnelClearanceM: number | null;
}
export interface RfTerrainProfile {
  status: RfTerrainStatus;
  distanceKm: number;
  points: RfTerrainProfilePoint[];
  freeSpaceLossDb: number;
  diffractionLossDb: number | null;
  receivedDbm: number | null;
  marginDb: number | null;
  planningMarginDb?: number | null;
  reserveDb?: number;
  minimumLosClearanceM: number | null;
  minimumFresnelClearanceM: number | null;
  obstructionIndex: number | null;
}
export interface RfTerrainRadialSample {
  position: Position;
  distanceKm: number;
  status: RfTerrainStatus;
  marginDb: number | null;
}
export interface RfTerrainRadial {
  bearingDegrees: number;
  clearDistanceKm: number;
  stopDistanceKm: number | null;
  status: RfTerrainStatus;
  samples: RfTerrainRadialSample[];
}
export interface RfTerrainAnalysis {
  engineering?: RfEngineeringSettings;
  kind: 'path' | 'radial';
  origin: Position;
  receiver: Position | null;
  maxDistanceKm: number;
  path: RfTerrainProfile | null;
  radials: RfTerrainRadial[];
  warnings: string[];
  sampleCount: number;
  missingSamples: number;
  belowSeaLevelSamples: number;
}
