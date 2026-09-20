import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { server } from '@/test/server';
import { workspaceRevision } from '@/lib/workspaceAccess';

import {
  createMapWorkspaceDocument,
  getMapWorkspaceDocument,
  listMapWorkspaceDocuments,
  removeMapWorkspaceDocument,
  updateMapWorkspaceDocument,
} from './mapWorkspace';

const document = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  kind: 'drawings' as const,
  title: 'Study',
  payload: { version: 1, objects: [], selectedId: null },
  revision: 1,
  created_by: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  team_id: null,
  created_at: '2026-09-20T00:00:00Z',
  updated_at: '2026-09-20T00:00:00Z',
};

describe('map workspace API', () => {
  it('requests an explicit bounded page without fetching further pages', async () => {
    let calls = 0;
    server.use(
      http.get('/api/map/workspaces', ({ request }) => {
        calls += 1;
        const query = new URL(request.url).searchParams;
        expect(query.get('offset')).toBe('100');
        expect(query.get('limit')).toBe('100');
        return HttpResponse.json([document]);
      }),
    );
    expect(
      await listMapWorkspaceDocuments('drawings', undefined, { offset: 100, limit: 100 }),
    ).toEqual([document]);
    expect(calls).toBe(1);
  });
  it('lists one kind and gets the selected document', async () => {
    server.use(
      http.get('/api/map/workspaces', ({ request }) => {
        expect(new URL(request.url).searchParams.get('kind')).toBe('drawings');
        return HttpResponse.json([document]);
      }),
      http.get('/api/map/workspaces/:id', ({ params }) => {
        expect(params.id).toBe(document.id);
        return HttpResponse.json(document);
      }),
    );
    expect(await listMapWorkspaceDocuments('drawings')).toEqual([document]);
    expect(await getMapWorkspaceDocument(document.id)).toEqual(document);
  });

  it('preserves expected revisions and sends explicit delete', async () => {
    const create = { kind: document.kind, title: document.title, payload: document.payload };
    const update = { title: 'Revised', payload: document.payload, expected_revision: 1 };
    server.use(
      http.post('/api/map/workspaces', async ({ request }) => {
        expect(await request.json()).toEqual(create);
        return HttpResponse.json(document);
      }),
      http.patch('/api/map/workspaces/:id', async ({ request }) => {
        expect(await request.json()).toEqual(update);
        return HttpResponse.json({ ...document, title: 'Revised', revision: 2 });
      }),
      http.delete('/api/map/workspaces/:id', () => new HttpResponse(null, { status: 204 })),
    );
    expect(await createMapWorkspaceDocument(create)).toEqual(document);
    expect((await updateMapWorkspaceDocument(document.id, update)).revision).toBe(2);
    await expect(removeMapWorkspaceDocument(document.id)).resolves.toBeUndefined();
  });

  it('invalidates authority after a denied mutation', async () => {
    server.use(
      http.delete('/api/map/workspaces/:id', () =>
        HttpResponse.json(
          { error: { code: 'forbidden', message: 'Not allowed' } },
          { status: 403 },
        ),
      ),
    );
    const before = workspaceRevision();
    await expect(removeMapWorkspaceDocument(document.id)).rejects.toMatchObject({ status: 403 });
    expect(workspaceRevision()).toBe(before + 1);
  });
});
