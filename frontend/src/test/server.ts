import { setupServer } from 'msw/node';

import { handlers } from './handlers';
import { runtimeHandlers } from './handlers.runtime';
import { capabilityHandlers } from './handlers.capabilities';
import { researchUsageHandlers } from './handlers.researchUsage';

export const server = setupServer(
  ...runtimeHandlers,
  ...handlers,
  ...researchUsageHandlers,
  ...capabilityHandlers,
);
