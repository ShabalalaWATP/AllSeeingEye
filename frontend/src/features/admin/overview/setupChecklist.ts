/** First-run set-up steps, derived only from state the administration API already returns. */
import type { LlmConnection, LlmProfilesResponse } from '@/lib/api/llm';

import { summariseConnections } from './overviewSummaries';

export interface SetupState {
  profiles: LlmProfilesResponse;
  connections: readonly LlmConnection[];
  /** `null` when that check could not be made; the step then reads as unknown. */
  emailRelay: boolean | null;
  osMaps: boolean | null;
  feedsContact: boolean | null;
}

export interface SetupStep {
  id: 'connect' | 'test' | 'assign' | 'email' | 'os_maps' | 'feeds_contact';
  title: string;
  detail: string;
  done: boolean | null;
  essential: boolean;
  /** An in-app page where the step is done. */
  to?: string;
  /** A server setting, for steps done in the installation's environment. */
  setting?: string;
}

export interface SetupChecklist {
  steps: SetupStep[];
  essentialDone: boolean;
  allDone: boolean;
  remainingOptional: number;
}

export function setupChecklist(state: SetupState): SetupChecklist {
  const text = state.profiles.items.filter((item) =>
    item.roles.some((role) => role !== 'embeddings'),
  );
  const tested = text.some((item) => item.is_tested && item.tested_revision === item.revision);
  const global = summariseConnections(state.profiles, state.connections).global;
  const steps: SetupStep[] = [
    {
      id: 'connect',
      title: 'Connect an AI provider',
      detail: 'Add a model with its provider key. The key is encrypted on the server.',
      done: text.length > 0,
      essential: true,
      to: '/admin/llm',
    },
    {
      id: 'test',
      title: 'Test the connection',
      detail: 'A small test request checks that the saved settings answer. It can incur a charge.',
      done: tested,
      essential: true,
      to: '/admin/llm',
    },
    {
      id: 'assign',
      title: 'Assign it to research',
      detail:
        'Apply a tested connection as the app default so research, reports and the Eye can use it.',
      done: global?.tested === true,
      essential: true,
      to: '/admin/llm',
    },
    {
      id: 'email',
      title: 'Email relay (optional)',
      detail: 'Sends account emails and email sign-in codes. Set the host and sender together.',
      done: state.emailRelay,
      essential: false,
      setting: 'ASE_SMTP_HOST and ASE_SMTP_FROM_EMAIL',
    },
    {
      id: 'os_maps',
      title: 'Ordnance Survey maps key (optional)',
      detail: 'Adds the OS base layers to the map. The key stays on the server.',
      done: state.osMaps,
      essential: false,
      setting: 'ASE_OS_MAPS_KEY',
    },
    {
      id: 'feeds_contact',
      title: 'Feeds contact (optional)',
      detail: 'A public operator email that upstream feeds ask for. Route planning needs it too.',
      done: state.feedsContact,
      essential: false,
      setting: 'ASE_FEEDS_CONTACT',
    },
  ];
  const essentialDone = steps.every((step) => !step.essential || step.done === true);
  const remainingOptional = steps.filter((step) => !step.essential && step.done !== true).length;
  return {
    steps,
    essentialDone,
    allDone: essentialDone && remainingOptional === 0,
    remainingOptional,
  };
}
