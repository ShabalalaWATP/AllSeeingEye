import type { LlmConnection, LlmProfile } from '@/lib/api/llm';
import type { Team } from '@/lib/api/teams';
import type { User } from '@/lib/api/schemas';

export interface ModelSetupAudience {
  scope: 'global' | 'team' | 'user';
  targetIds: string[];
}

export interface ModelSetupProps {
  initial?: LlmProfile;
  profiles: LlmProfile[];
  teams: Team[];
  users: User[];
  connections: LlmConnection[];
  onClose: () => void;
  onSaved: (profile: LlmProfile) => void;
  onApply: (profile: LlmProfile, audience: ModelSetupAudience) => Promise<void>;
}

export interface ModelSetupFields {
  name: string;
  provider: 'openai' | 'bedrock' | 'custom';
  baseUrl: string;
  region: string;
  apiKey: string;
  model: string;
  effort: NonNullable<LlmProfile['reasoning_effort']> | '';
}

export const MODEL_SETUP_STEPS = ['Name', 'API key', 'Model', 'Reasoning', 'Test', 'Audience'];
export const MODEL_SETUP_MAX_TARGETS = 100;
