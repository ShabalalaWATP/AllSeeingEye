import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { EvidenceProjectDetails } from './EvidenceProjectDetails';

const base = report.version.evidence[0]!;
const project = {
  dataset_id: 'aiddata-geogcdf',
  release_id: 'v3.0.1',
  project_id: '35756',
  source_sha256: 'a'.repeat(64),
  recipient_iso3: 'LAO',
  reported_status: 'Completion',
  precision: 'mixed',
  attribution: 'AidData; OpenStreetMap contributors',
  data_licence: 'ODC-By-1.0',
  geometry_licence: 'ODbL-1.0',
  limitations: '<img src=x onerror=alert(1)>',
  commitment_year: 2011,
  implementation_year: null,
  completion_year: 2012,
};

it('shows project years, uncertainty and licensing as source text', () => {
  const { container } = render(<EvidenceProjectDetails item={{ ...base, project }} />);
  expect(screen.getByRole('region', { name: 'Project record' })).toBeInTheDocument();
  expect(screen.getByText('2011 (exact date unknown)')).toBeInTheDocument();
  expect(screen.getAllByText('Unknown')).toHaveLength(2);
  expect(screen.getByText('ODbL-1.0')).toBeInTheDocument();
  expect(screen.getByText(project.limitations)).toBeInTheDocument();
  expect(container.querySelector('img')).toBeNull();
  expect(screen.getByText(/does not establish a payment/)).toBeInTheDocument();
  expect(screen.queryByText('Acquired')).not.toBeInTheDocument();
});

it('does not invent project information for legacy evidence', () => {
  render(<EvidenceProjectDetails item={base} />);
  expect(screen.queryByRole('region', { name: 'Project record' })).not.toBeInTheDocument();
});

it.each(['0', '123.12345678901234567890'])('retains exact monetary text %s', (amount) => {
  render(
    <EvidenceProjectDetails
      item={{
        ...base,
        project,
        attributes: [{ key: 'aiddata_amount_constant_usd_2021', value: amount }],
      }}
    />,
  );
  expect(screen.getByText('Reported amount (constant 2021 USD)')).toBeInTheDocument();
  expect(screen.getByText(amount)).toBeInTheDocument();
});
