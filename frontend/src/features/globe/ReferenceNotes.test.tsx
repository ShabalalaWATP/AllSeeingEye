import { render, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { liveEvent } from '@/test/fixtures';
import { applySession } from '@/test/render';
import { server } from '@/test/server';

import { ReferenceNotes, referenceQueries } from './ReferenceNotes';

const aircraft = liveEvent({
  id: 'a1',
  category: 'aviation',
  subtype: 'military_aircraft',
  title: 'RRR7001',
  attributes: { registration: 'ZZ-338', aircraft_type: 'A332', icao_hex: '43c6e1' },
});
const vessel = liveEvent({
  id: 'v1',
  category: 'maritime',
  subtype: 'vessel_position',
  title: 'HMS ARGYLL',
  attributes: { mmsi: '165327752', ship_type_code: 35 },
});

describe('reference notes', () => {
  it('derives lookups from broadcast identifiers only', () => {
    expect(referenceQueries(aircraft)).toEqual([
      { kind: 'aircraft', keys: ['ZZ-338'] },
      { kind: 'aircraft_type', keys: ['A332'] },
    ]);
    expect(referenceQueries(vessel)).toEqual([{ kind: 'vessel', keys: ['165327752'] }]);
    expect(referenceQueries(liveEvent({ category: 'news', attributes: { mmsi: '1' } }))).toEqual(
      [],
    );
  });

  it('shows matching notes with links and the identity caveat', async () => {
    applySession('user');
    const seen = vi.fn();
    server.use(
      http.get('/api/reference', ({ request }) => {
        const url = new URL(request.url);
        seen(url.searchParams.get('kind'), url.searchParams.get('keys'));
        if (url.searchParams.get('kind') !== 'aircraft_type')
          return HttpResponse.json({
            items: [],
            retrieved_at: '2026-09-13T18:00:00Z',
            caveat: 'c',
          });
        return HttpResponse.json({
          items: [
            {
              kind: 'aircraft_type',
              key: 'A332',
              name: 'Airbus A330-200 (including MRTT)',
              description: 'Wide-body airliner type also flown as a tanker-transport.',
              detail: 'Airliner or tanker-transport',
              links: [
                { label: 'Wikipedia', url: 'https://en.wikipedia.org/wiki/Airbus_A330_MRTT' },
              ],
              provenance: 'Curated',
            },
          ],
          retrieved_at: '2026-09-13T18:00:00Z',
          caveat: 'c',
        });
      }),
    );
    render(<ReferenceNotes event={aircraft} />);
    const notes = await screen.findByRole('region', { name: 'Reference notes' });
    expect(within(notes).getByText('Airbus A330-200 (including MRTT)')).toBeVisible();
    expect(within(notes).getByText(/Aircraft type · A332/)).toBeVisible();
    expect(within(notes).getByRole('link', { name: 'Wikipedia' })).toHaveAttribute(
      'rel',
      'noreferrer',
    );
    expect(
      within(notes).getByText(/not confirmation that this is the object on record/),
    ).toBeVisible();
    await waitFor(() => expect(seen).toHaveBeenCalledTimes(2));
    expect(seen).toHaveBeenCalledWith('aircraft', 'ZZ-338');
  });

  it('renders nothing when no note matches or the lookup fails', async () => {
    applySession('user');
    server.use(http.get('/api/reference', () => HttpResponse.json({}, { status: 503 })));
    const { container } = render(<ReferenceNotes event={vessel} />);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByRole('region', { name: 'Reference notes' })).not.toBeInTheDocument();
  });
});
