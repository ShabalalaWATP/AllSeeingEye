import { http, HttpResponse } from 'msw';

export const libraryHandlers = [
  http.get('/api/me/library', () =>
    HttpResponse.json({ items: [], total: 0, offset: 0, limit: 20 }),
  ),
  http.get('/api/me/library/:id', () =>
    HttpResponse.json({ favourite: false, tags: [], note: null, updated_at: null }),
  ),
  http.put('/api/me/library/:id', async ({ request }) =>
    HttpResponse.json({
      ...((await request.json()) as object),
      updated_at: '2026-09-01T00:00:00Z',
    }),
  ),
  http.delete('/api/me/library/:id', () => new HttpResponse(null, { status: 204 })),
];
