import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { cyberItems } from '@/test/fixtures.cyber';
import { CyberVulnerabilities } from './CyberVulnerabilities';

it('sorts EPSS independently of CVSS, retaining unavailable values and known exploitation', async () => {
  const base = cyberItems.find((item) => item.kev !== null);
  if (!base?.kev) throw new Error('Missing KEV fixture');
  const rows = [
    {
      ...base,
      id: 'a',
      kev: {
        ...base.kev,
        cve: 'CVE-2026-1000',
        epss: { probability: 0.2, percentile: 0.6, date: '2026-09-29' },
        cvss: null,
      },
    },
    {
      ...base,
      id: 'b',
      kev: {
        ...base.kev,
        cve: 'CVE-2026-2000',
        epss: null,
        cvss: {
          base_score: 9.8,
          version: '3.1',
          vector: 'CVSS:3.1/AV:N',
          source: 'vendor@example.test',
          updated_at: '2026-09-28',
        },
      },
    },
    {
      ...base,
      id: 'c',
      kev: {
        ...base.kev,
        cve: 'CVE-2026-3000',
        epss: { probability: 0.9, percentile: 0.99, date: '2026-09-29' },
        cvss: null,
      },
    },
  ];
  render(<CyberVulnerabilities items={rows} />);
  await userEvent
    .setup()
    .selectOptions(screen.getByRole('combobox', { name: 'Sort vulnerabilities' }), 'epss');
  expect(
    screen.getAllByRole('heading', { level: 3 }).map((element) => element.textContent),
  ).toEqual(['CVE-2026-3000', 'CVE-2026-1000', 'CVE-2026-2000']);
  expect(screen.getByText(/FIRST EPSS probability model: 90.00%/)).toHaveTextContent('2026-09-29');
  expect(screen.getByText(/CVSS 3.1 base severity: 9.8/)).toHaveTextContent('2026-09-28');
  expect(screen.getByText('FIRST EPSS: unavailable.')).toBeVisible();
  expect(screen.getAllByText('NVD CVSS: unavailable.')).toHaveLength(2);
  expect(
    screen.getAllByText(/CISA already lists this vulnerability as known exploited/),
  ).toHaveLength(3);
});
