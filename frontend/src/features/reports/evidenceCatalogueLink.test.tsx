import { render, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';

import { report } from '@/test/fixtures';

import { EvidenceAnnex } from './EvidenceAnnex';

it('links the annex to the current source catalogue without a router', () => {
  render(<EvidenceAnnex evidence={report.version.evidence} findings={[]} status="ready" />);
  const annex = within(screen.getByRole('region', { name: 'Evidence annex' }));
  const link = annex.getByRole('link', { name: 'Compare current grades in the source catalogue' });
  expect(link).toHaveAttribute('href', '/sources');
});
