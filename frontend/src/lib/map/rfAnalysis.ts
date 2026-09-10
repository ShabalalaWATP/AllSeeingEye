import type { Position } from './geoJsonTypes';
import type { RfInputs } from './rfPlanning';
import type { RfTerrainAnalysis, RfTerrainSamplePlan } from './rfTerrainTypes';
import type { TerrainElevations } from '@/lib/api/terrain';
import type { GroundwaveResult } from '@/lib/api/groundwave';
import type { HfSkywaveMapEstimate } from './hfSkywaveLayers';
import type { RfEngineeringSettings } from './rfEngineering';

export type RfAnalysis =
  | {
      kind: 'terrain';
      terrain: RfTerrainAnalysis;
      plan: RfTerrainSamplePlan;
      elevations: TerrainElevations;
      input: RfInputs;
    }
  | {
      kind: 'hf-groundwave';
      engineering?: RfEngineeringSettings;
      result: GroundwaveResult;
      origin: Position;
      receiver: Position | null;
      input: RfInputs;
    }
  | { kind: 'hf-skywave'; estimate: HfSkywaveMapEstimate };
