import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { photoAssessment, photoId } from '@/test/photoGeolocationFixture';
import { server } from '@/test/server';

import {
  discardResearchInput,
  geolocateResearchInput,
  researchGeolocationSchema,
} from './researchGeolocation';
import { workspaceRevision } from '@/lib/workspaceAccess';

describe('private photo geolocation contract', () => {
  beforeEach(() => useAuthStore.getState().setSession(tokenFor(plainUser)));

  it('sends an authenticated explicit-disclosure request with the input reference and no image bytes', async () => {
    const requests: unknown[] = [];
    const headers: (string | null)[] = [];
    server.use(
      http.post('/api/research/inputs/:id/geolocation', async ({ request, params }) => {
        expect(params.id).toBe(photoId);
        requests.push(await request.json());
        headers.push(request.headers.get('Authorization'));
        return HttpResponse.json(photoAssessment());
      }),
    );
    const result = await geolocateResearchInput(
      photoId,
      {
        consent_to_send_image: true,
        question: 'Where?',
        hints: '',
        team_id: null,
      },
      new AbortController().signal,
    );
    expect(result.candidate_status).toBe('unverified');
    expect(headers).toEqual(['Bearer user-access-token']);
    expect(requests).toEqual([
      {
        consent_to_send_image: true,
        question: 'Where?',
        hints: '',
        team_id: null,
      },
    ]);
  });

  it.each([
    'inconsistent status',
    'out of range coordinates',
    'unsafe preview',
    'too many candidates',
  ])('rejects %s at the response boundary', async (kind) => {
    const result = photoAssessment();
    if (kind === 'inconsistent status') result.status = 'unknown';
    else if (kind === 'out of range coordinates') result.candidates[0]!.coordinates!.latitude = 91;
    else if (kind === 'unsafe preview')
      result.input.previews![0]!.png_base64 = '<svg onload="alert(1)">';
    else result.candidates = Array.from({ length: 4 }, () => result.candidates[0]!);
    server.use(http.post('/api/research/inputs/:id/geolocation', () => HttpResponse.json(result)));
    await expect(
      geolocateResearchInput(
        photoId,
        { consent_to_send_image: true, question: 'Where?', hints: '' },
        new AbortController().signal,
      ),
    ).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('accepts a valid unknown outcome with no coordinates or invented country', () => {
    expect(
      researchGeolocationSchema.safeParse(
        photoAssessment({
          status: 'unknown',
          candidates: [],
          summary: 'Insufficient distinctive detail.',
        }),
      ).success,
    ).toBe(true);
  });

  it.each([204, 404])(
    'accepts explicit cleanup status %s without changing workspace authority',
    async (status) => {
      server.use(
        http.delete(
          '/api/research/inputs/:id',
          () =>
            new HttpResponse(
              status === 404
                ? JSON.stringify({ error: { code: 'not_found', message: 'Input not found.' } })
                : null,
              { status },
            ),
        ),
      );
      const revision = workspaceRevision();
      await discardResearchInput(photoId, new AbortController().signal);
      expect(workspaceRevision()).toBe(revision);
    },
  );

  it('does not hide a server failure during explicit cleanup', async () => {
    server.use(
      http.delete('/api/research/inputs/:id', () => new HttpResponse(null, { status: 500 })),
    );
    await expect(discardResearchInput(photoId, new AbortController().signal)).rejects.toMatchObject(
      { status: 500 },
    );
  });
});
