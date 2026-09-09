import type { RfInputs } from './rfPlanning';
import type { RfEnvironment } from './rfDraft';

export interface RfPreset {
  id: string;
  group?: 'bowman' | 'military';
  basis?: 'published' | 'illustrative';
  specification?: { band: string; output: string };
  label: string;
  note: string;
  values: RfInputs;
  referenceUrl?: string;
  referenceLabel?: string;
  propagation?: 'terrain' | 'hf-groundwave' | 'hf-skywave';
  environment?: Partial<RfEnvironment>;
}
