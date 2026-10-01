/** What a research progress view may show: real server stages only, never estimated percentages. */
import type { components } from '@/lib/api/types.gen';

export type ResearchStage = components['schemas']['ResearchStage'];
export type ResearchOutcome = 'running' | 'completed' | 'failed' | 'cancelled';

export interface ResearchProgressSnapshot {
  /** Durable jobs use this only while the initial submission is being acknowledged. */
  submission?: boolean;
  stage: ResearchStage | null;
  outcome: ResearchOutcome;
  unavailable: boolean;
}
