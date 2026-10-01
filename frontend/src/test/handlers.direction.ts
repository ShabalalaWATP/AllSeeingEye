/** MSW handlers for the direction API: areas of interest and collection plans. */
import { http, HttpResponse } from 'msw';

import { aoi, plan, planEvidence } from './fixtures.direction';

interface AreaBody {
  name: string;
  kind: string;
  bbox: number[];
  countries: string[];
}

interface SirBody {
  text: string;
  keywords?: string[];
  categories?: string[];
}

interface PlanBody {
  name: string;
  description: string;
  aoi_id: string | null;
  countries: string[];
  enabled: boolean;
  pirs: { text: string; sirs: SirBody[] }[];
}

/** The plan the server would store for a create or update body, with positional codes. */
export function planFromBody(body: Partial<PlanBody>) {
  return {
    ...plan,
    name: String(body.name),
    description: body.description ?? '',
    aoi_id: body.aoi_id ?? null,
    countries: body.countries ?? [],
    enabled: body.enabled ?? true,
    pirs: (body.pirs ?? []).map((pir, index) => ({
      code: `PIR-${index + 1}`,
      text: pir.text,
      sirs: pir.sirs.map((sir, position) => ({
        code: `SIR-${index + 1}.${position + 1}`,
        text: sir.text,
        keywords: sir.keywords ?? [],
        categories: sir.categories ?? [],
      })),
    })),
  };
}

const notFound = (what: string) =>
  HttpResponse.json(
    { error: { code: 'not_found', message: `${what} not found.` } },
    { status: 404 },
  );

export const directionHandlers = [
  http.get('/api/direction/aois', () => HttpResponse.json({ items: [aoi] })),

  http.post('/api/direction/aois', async ({ request }) => {
    const body = (await request.json()) as Partial<AreaBody>;
    return HttpResponse.json(
      {
        ...aoi,
        id: 'a3a3a3a3-a3a3-4a3a-8a3a-a3a3a3a3a3a3',
        name: String(body.name),
        kind: String(body.kind),
        bbox: body.bbox ?? null,
        countries: body.countries ?? [],
      },
      { status: 201 },
    );
  }),

  http.delete('/api/direction/aois/:id', ({ params }) =>
    params.id === aoi.id ? new HttpResponse(null, { status: 204 }) : notFound('Area'),
  ),

  http.get('/api/direction/plans', () => HttpResponse.json({ items: [plan] })),

  http.post('/api/direction/plans', async ({ request }) => {
    const body = (await request.json()) as Partial<PlanBody>;
    return HttpResponse.json(
      { ...planFromBody(body), id: 'b4b4b4b4-b4b4-4b4b-8b4b-b4b4b4b4b4b4' },
      { status: 201 },
    );
  }),

  http.get('/api/direction/plans/:id/definition', ({ params }) =>
    params.id === plan.id ? HttpResponse.json(plan) : notFound('Plan'),
  ),

  http.put('/api/direction/plans/:id', async ({ params, request }) => {
    if (params.id !== plan.id) return notFound('Plan');
    const body = (await request.json()) as Partial<PlanBody>;
    return HttpResponse.json({ ...planFromBody(body), updated_at: '2026-09-04T11:00:00Z' });
  }),

  http.get('/api/direction/plans/:id', ({ params }) =>
    params.id === plan.id ? HttpResponse.json(planEvidence) : notFound('Plan'),
  ),

  http.delete('/api/direction/plans/:id', ({ params }) =>
    params.id === plan.id ? new HttpResponse(null, { status: 204 }) : notFound('Plan'),
  ),
];
