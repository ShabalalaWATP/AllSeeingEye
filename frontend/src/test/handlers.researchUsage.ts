import { http, HttpResponse } from 'msw';

import { researchAllowance, researchUsagePage } from './fixtures.researchUsage';

export const researchUsageHandlers = [
  http.get('/api/research-usage/me', () => HttpResponse.json(researchAllowance())),
  http.get('/api/admin/research-usage', () => HttpResponse.json(researchUsagePage())),
];
