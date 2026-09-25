import { setupServer } from 'msw/node';

import { handlers } from './handlers';
import { capabilityHandlers } from './handlers.capabilities';
import { researchUsageHandlers } from './handlers.researchUsage';

export const server = setupServer(...handlers, ...researchUsageHandlers, ...capabilityHandlers);
