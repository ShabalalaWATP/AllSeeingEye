import { render, screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeAll, describe, expect, it, vi } from 'vitest';

import {
  civilianHarm,
  confirmedLosses,
  ukraineFrontlineOff,
  ukraineFrontlineReady,
  ukraineSpottedOff,
  ukraineSpottedReady,
} from '@/test/fixtures.ukraineFigures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { HarmCard, OryxCards } from './ConfirmedFigures';
import { buildFrontlineLayers, buildSpottedLayer } from './providerLayers';

beforeAll(async () => {
  await import('./UkrainePage');
});

describe('confirmed and documented figures', () => {
  it('shows Oryx totals per side with a status split and the latest HRMMU month', () => {
    render(
      <ul>
        <OryxCards confirmed={confirmedLosses} />
        <HarmCard harm={civilianHarm} />
      </ul>,
    );
    expect(screen.getByText('24,066')).toBeInTheDocument();
    expect(screen.getByText('12,097')).toBeInTheDocument();
    expect(screen.getAllByText('Visually confirmed')).toHaveLength(2);
    expect(screen.getByText('Civilians killed, July 2026')).toBeInTheDocument();
    expect(screen.getByText('437')).toBeInTheDocument();
    expect(screen.getByText('Documented')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Monthly update' })).toHaveAttribute(
      'href',
      civilianHarm.months[0]!.url,
    );
  });

  it('renders nothing for a side without a total or a harm feed without figures', () => {
    const { container } = render(
      <ul>
        <OryxCards confirmed={{ ...confirmedLosses, rows: [], days: [] }} />
        <HarmCard harm={{ ...civilianHarm, months: [civilianHarm.months[1]!] }} />
      </ul>,
    );
    expect(container.querySelectorAll('li')).toHaveLength(0);
  });
});

describe('lens sections on the page', () => {
  it('charts each lens by group and lists matching items with casualty details', async () => {
    renderApp('/conflicts/ukraine', 'user');
    const casualties = await screen.findByRole(
      'region',
      { name: 'Casualties news' },
      { timeout: 5000 },
    );
    expect(
      within(casualties).getByRole('table', { name: /verified by the UN monitoring mission/ }),
    ).toBeInTheDocument();
    expect(within(casualties).getAllByText('not stated')).toHaveLength(2);
    const references = within(casualties).getByRole('list', { name: 'Casualty references' });
    expect(within(references).getByText('Documented')).toBeInTheDocument();
    expect(within(references).getByText('Reported')).toBeInTheDocument();
    expect(
      within(casualties).getByText('No retained item matches this lens in the window.'),
    ).toBeInTheDocument();
    const workforce = screen.getByRole('region', { name: 'Workforce news' });
    expect(
      within(workforce).getByRole('link', { name: 'Mobilisation rules tightened' }),
    ).toBeInTheDocument();
    expect(
      within(workforce).getByRole('img', { name: /Workforce items per day/ }),
    ).toBeInTheDocument();
    const equipment = screen.getByRole('region', { name: 'Equipment news' });
    expect(within(equipment).getByText('state media')).toBeInTheDocument();
    const legend = screen.getByRole('list', { name: 'Provider layers' });
    expect(legend).toHaveTextContent('Frontline provider: off.');
    expect(legend).toHaveTextContent('Spotted losses: off.');
  });

  it('names an enabled provider and its markers in the legend', async () => {
    server.use(
      http.get('/api/conflicts/ukraine/frontline', () => HttpResponse.json(ukraineFrontlineReady)),
      http.get('/api/conflicts/ukraine/spotted', () => HttpResponse.json(ukraineSpottedReady)),
    );
    renderApp('/conflicts/ukraine', 'user');
    const note = await screen.findByRole('list', { name: 'Provider layers' }, { timeout: 5000 });
    expect(note).toHaveTextContent('DeepStateMap.live (ready, assessed 12.09 o 21:04)');
    expect(note).toHaveTextContent('WarSpotting (ready, 1 markers)');
    const legend = screen.getByRole('list', { name: 'Map legend' });
    expect(legend).toHaveTextContent('Provider: occupied');
    expect(legend).toHaveTextContent('Provider: front line');
    expect(legend).toHaveTextContent('Photographed losses (WarSpotting)');
  });
});

describe('provider layers', () => {
  it('builds area and line layers only when the provider has geometry', () => {
    expect(buildFrontlineLayers(null)).toEqual([]);
    expect(buildFrontlineLayers(ukraineFrontlineOff)).toEqual([]);
    const layers = buildFrontlineLayers(ukraineFrontlineReady);
    expect(layers.map((layer) => layer.id)).toEqual([
      'ukraine-frontline-areas',
      'ukraine-frontline-lines',
    ]);
    const areas = layers[0]!.props as unknown as {
      getFillColor: (f: { properties: { kind: 'occupied' } }) => number[];
    };
    expect(areas.getFillColor({ properties: { kind: 'occupied' } })).toEqual([244, 63, 94, 40]);
    expect(
      buildFrontlineLayers({
        ...ukraineFrontlineReady,
        features: [ukraineFrontlineReady.features[0]!],
      }),
    ).toHaveLength(1);
  });

  it('builds a pickable loss layer that reports hover', () => {
    const onHover = vi.fn();
    expect(buildSpottedLayer(ukraineSpottedOff, onHover)).toEqual([]);
    const [layer] = buildSpottedLayer(ukraineSpottedReady, onHover);
    const props = layer!.props as unknown as {
      getPosition: (loss: (typeof ukraineSpottedReady.losses)[number]) => number[];
      onHover: (info: { object?: unknown; x: number; y: number }) => void;
    };
    expect(props.getPosition(ukraineSpottedReady.losses[0]!)).toEqual([37.055325, 48.122783]);
    props.onHover({ object: ukraineSpottedReady.losses[0], x: 1, y: 2 });
    expect(onHover).toHaveBeenCalledWith(ukraineSpottedReady.losses[0], 1, 2);
    props.onHover({ x: 0, y: 0 });
    expect(onHover).toHaveBeenLastCalledWith(null, 0, 0);
  });
});
