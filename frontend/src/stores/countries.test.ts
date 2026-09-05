import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import { server } from '@/test/server';

import { initialCountriesState, useCountriesStore } from './countries';

describe('countries store', () => {
  beforeEach(() => {
    useCountriesStore.setState({ ...initialCountriesState });
  });

  it('loads once and indexes by code', async () => {
    let requests = 0;
    server.use(
      http.get('/api/countries', () => {
        requests += 1;
        return HttpResponse.json({
          items: [
            {
              iso2: 'GB',
              iso3: 'GBR',
              name: 'United Kingdom',
              bounds: [0, 0, 1, 1],
              centroid: [0.5, 0.5],
            },
          ],
        });
      }),
    );
    await useCountriesStore.getState().load();
    await useCountriesStore.getState().load();
    const state = useCountriesStore.getState();
    expect(requests).toBe(1);
    expect(state.loaded).toBe(true);
    expect(state.byIso.GB?.name).toBe('United Kingdom');
    expect(state.items).toHaveLength(1);
  });

  it('records a failure', async () => {
    server.use(
      http.get('/api/countries', () =>
        HttpResponse.json({ error: { code: 'x', message: 'No atlas.' } }, { status: 500 }),
      ),
    );
    await useCountriesStore.getState().load();
    expect(useCountriesStore.getState().error).toBe('No atlas.');
    expect(useCountriesStore.getState().loaded).toBe(false);
  });
});
