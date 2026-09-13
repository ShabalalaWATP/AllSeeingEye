import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { Infrastructure, Site } from '@/lib/api/infrastructure';
import { infrastructureSchema } from '@/lib/api/infrastructure';

import { InfrastructureInspector } from './InfrastructureInspector';
import { buildInfrastructureLayers } from './infrastructureLayers';

const refinery: Site = {
  id: 'wd-q16510565',
  kind: 'refinery',
  name: 'Ras Tanura Refinery',
  operator: 'Saudi Aramco',
  owner: null,
  country: 'SA',
  longitude: 50.1079,
  latitude: 26.6919,
  precision: 'site',
  description: '',
  significance: 'Saudi Aramco’s largest refinery and the Ras Tanura export terminal.',
  detail: 'Refinery and marine terminal on the Gulf coast.',
  website: null,
  wikipedia: 'https://en.wikipedia.org/wiki/Ras_Tanura_Refinery',
  links: [
    { label: 'Wikipedia', url: 'https://en.wikipedia.org/wiki/Ras_Tanura_Refinery' },
    { label: 'Saudi Aramco website', url: 'https://www.aramco.com/' },
  ],
  source_url: 'https://www.wikidata.org/wiki/Q16510565',
  note: 'Mapped position only.',
};
const fab: Site = {
  ...refinery,
  id: 'seed-asml',
  kind: 'equipment',
  name: 'ASML',
  operator: 'ASML',
  country: 'NL',
  longitude: 5.4,
  latitude: 51.4,
  precision: 'city',
  significance: 'Sole maker of EUV lithography systems.',
  detail: 'Veldhoven headquarters and EUV assembly.',
  wikipedia: null,
  links: [],
  source_url: 'https://www.wikidata.org/',
  note: 'Placed at the city named in the curated entry.',
};
const data: Infrastructure = {
  cables: [],
  ground_stations: [],
  nuclear_facilities: [],
  data_centres: [],
  energy_sites: [refinery],
  semiconductor_sites: [fab],
  snapshot_date: '2026-09-13',
  cable_attribution: 'OSM',
  cable_licence_url: 'https://www.openstreetmap.org/copyright',
  nuclear_attribution: 'WRI',
  nuclear_licence_url: 'https://creativecommons.org/licenses/by/4.0/',
  nuclear_dataset_version: 'test',
  nuclear_snapshot_date: '2026-09-09',
  data_centre_attribution: 'OSM',
  data_centre_licence_url: 'https://www.openstreetmap.org/copyright',
  data_centre_snapshot_date: '2026-09-13',
  site_attribution: 'Wikidata and OpenStreetMap contributors',
  site_licence_url: 'https://www.openstreetmap.org/copyright',
  site_snapshot_date: '2026-09-13',
};

describe('energy and semiconductor site layers', () => {
  it('validates the site records and rejects unsafe links', () => {
    expect(infrastructureSchema.safeParse(data).success).toBe(true);
    expect(
      infrastructureSchema.safeParse({
        ...data,
        energy_sites: [{ ...refinery, wikipedia: 'javascript:alert(1)' }],
      }).success,
    ).toBe(false);
    expect(
      infrastructureSchema.safeParse({
        ...data,
        energy_sites: [{ ...refinery, precision: 'guess' }],
      }).success,
    ).toBe(false);
  });

  it('builds a layer per enabled site category with curated sites drawn larger', () => {
    const choose = vi.fn();
    const layers = buildInfrastructureLayers(
      {
        data,
        cablesEnabled: false,
        stationsEnabled: false,
        energyEnabled: true,
        semiconductorEnabled: true,
        selected: { kind: 'energy_site', item: refinery },
      },
      choose,
    );
    expect(layers.map((layer) => layer.id)).toEqual([
      'energy-sites',
      'selected-energy-site-halo',
      'semiconductor-sites',
    ]);
    const energy = layers[0]?.props as unknown as {
      getSize: (site: Site) => number;
      onClick: (info: { object?: Site }) => boolean;
    };
    expect(energy.getSize(refinery)).toBe(30);
    expect(energy.getSize({ ...refinery, id: 'other', significance: null })).toBe(18);
    energy.onClick({ object: refinery });
    expect(choose).toHaveBeenCalledWith({ kind: 'energy_site', item: refinery });
    expect(
      buildInfrastructureLayers(
        { data, cablesEnabled: false, stationsEnabled: false, selected: null },
        choose,
      ),
    ).toEqual([]);
  });

  it('shows purpose, owner, links and the city-level caveat in the inspector', () => {
    const { rerender } = render(
      <InfrastructureInspector
        selected={{ kind: 'energy_site', item: refinery }}
        onClose={vi.fn()}
      />,
    );
    const aside = screen.getByRole('complementary', { name: 'Infrastructure details' });
    expect(within(aside).getByText('Oil and gas facility · Refinery')).toBeVisible();
    expect(within(aside).getByText('Saudi Aramco')).toBeVisible();
    expect(within(aside).getByText(/largest refinery/)).toBeVisible();
    expect(within(aside).getByRole('link', { name: 'Wikipedia' })).toHaveAttribute(
      'href',
      'https://en.wikipedia.org/wiki/Ras_Tanura_Refinery',
    );
    expect(within(aside).getByRole('link', { name: 'Saudi Aramco website' })).toHaveAttribute(
      'href',
      'https://www.aramco.com/',
    );
    expect(within(aside).getByText(/marine terminal on the Gulf coast/)).toBeVisible();
    expect(within(aside).getByText(/not verified here/)).toBeVisible();
    rerender(
      <InfrastructureInspector
        selected={{ kind: 'semiconductor_site', item: fab }}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText('Semiconductor site · Equipment maker')).toBeVisible();
    expect(screen.getByText(/Placed at the named city/)).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Wikipedia' })).not.toBeInTheDocument();
  });
});
