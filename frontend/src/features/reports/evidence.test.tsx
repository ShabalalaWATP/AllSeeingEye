import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { report } from '@/test/fixtures';

import { EvidenceAnnex } from './ReportSections';

const rich = {
  ...report.version.evidence[0]!,
  label: 'E1',
  event_id: 'e1',
  source_id: 'source',
  source_name: 'Declared publisher',
  category: 'news',
  title: 'Original headline',
  summary: 'Original source snippet',
  url: 'https://example.org/source',
  published_at: '2026-09-04T22:00:00Z',
  grade: 'C3',
  grade_rationale: 'Unverified claim',
  country_iso: 'UA',
  flags: [],
  archive_url: null,
  title_en: 'Translated headline',
  language: 'uk',
  captured_at: '2026-09-05T01:00:00Z',
  observed_at: '2026-09-04T23:00:00Z',
  content_hash: 'a'.repeat(64),
  reliability: 'C',
  credibility: 3,
  geo_confidence: 'country',
  independence_key: 'Publisher group',
  story_id: 'topic-one',
  lon: 31,
  lat: 49,
};

describe('frozen evidence reader', () => {
  it('shows provenance on demand without a wide table', async () => {
    const user = userEvent.setup();
    render(<EvidenceAnnex evidence={[rich]} findings={[]} status="ready" />);
    const annex = screen.getByRole('region', { name: 'Evidence annex' });
    expect(within(annex).queryByRole('table')).not.toBeInTheDocument();
    await user.click(screen.getByText('Original headline'));
    expect(screen.getByText('Translated headline')).toBeVisible();
    expect(screen.getByText('Translation (unverified)')).toBeVisible();
    expect(screen.getByText('Unverified claim')).toBeVisible();
    expect(screen.getByText('a'.repeat(64))).toBeVisible();
    expect(screen.getByText('country')).toBeVisible();
    expect(screen.getByText('Publisher group')).toBeVisible();
    expect(screen.getByText(/grouping does not establish corroboration/)).toBeVisible();
  });

  it('makes absent legacy metadata explicit', async () => {
    const user = userEvent.setup();
    render(<EvidenceAnnex evidence={[report.version.evidence[0]!]} findings={[]} status="ready" />);
    await user.click(screen.getByText('Shelling in Kharkiv'));
    expect(screen.getByText('Location precision')).toBeVisible();
    expect(screen.getAllByText('Unknown').length).toBeGreaterThan(3);
  });

  it('keeps malicious text literal and unsafe destinations unlinked', async () => {
    const user = userEvent.setup();
    const title = '<img src=x onerror=alert(1)> [forged](javascript:alert(1))';
    const { container } = render(
      <EvidenceAnnex
        evidence={[
          {
            ...rich,
            title,
            url: 'javascript:alert(1)',
            archive_url: 'file:///private',
          },
        ]}
        findings={[]}
        status="ready"
      />,
    );
    await user.click(screen.getByText(title));
    expect(container.querySelector('img')).toBeNull();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByText(title)).toBeVisible();
  });

  it('explains an empty frozen evidence bundle', () => {
    render(<EvidenceAnnex evidence={[]} findings={[]} status="failed" />);
    expect(screen.getByText('No frozen evidence was saved for this version.')).toBeInTheDocument();
  });

  it.each(['https://user:password@example.org/source', 'https://example.org/\tforged'])(
    'does not open a deceptive source destination: %s',
    async (url) => {
      const user = userEvent.setup();
      render(<EvidenceAnnex evidence={[{ ...rich, url }]} findings={[]} status="ready" />);
      await user.click(screen.getByText('Original headline'));
      expect(screen.queryByRole('link')).not.toBeInTheDocument();
    },
  );

  it('keeps malformed legacy timestamps and blank metadata unknown', async () => {
    const user = userEvent.setup();
    render(
      <EvidenceAnnex
        evidence={[{ ...rich, observed_at: 'invalid', language: ' ', grade_rationale: '' }]}
        findings={[]}
        status="ready"
      />,
    );
    await user.click(screen.getByText('Original headline'));
    expect(screen.getByText('Not provided')).toBeVisible();
    expect(screen.getAllByText('Unknown')).toHaveLength(2);
    expect(screen.queryByText('Invalid Date')).not.toBeInTheDocument();
  });
});
