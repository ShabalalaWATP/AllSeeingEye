/** Default installation capabilities: AI research ready, no OS Maps key, no feeds contact. */
import { http, HttpResponse } from 'msw';

import type { components } from '@/lib/api/types.gen';

import { serverCapabilities } from './fixtures.researchMetadata';

export const navigationUnconfigured: components['schemas']['NavigationCapabilitiesOut'] = {
  provider: 'FOSSGIS Valhalla',
  operator_contact: '',
  available: false,
  configuration_message: 'Routing needs a valid public operator email in ASE_FEEDS_CONTACT.',
  privacy: 'Calculate route sends the entered coordinates to FOSSGIS, which may log requests.',
};

export const capabilityHandlers = [
  http.get('/api/capabilities', () => HttpResponse.json(serverCapabilities)),
  http.get('/api/navigation/capabilities', () => HttpResponse.json(navigationUnconfigured)),
];
