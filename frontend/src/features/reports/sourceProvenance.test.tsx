import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { EvidenceAnnex } from './EvidenceAnnex';
import { SourceProvenanceDetails } from '@/components/reports/SourceProvenanceDetails';
import { sourceDateSchema, textTransformationSchema } from '@/lib/api/sourceProvenance';
import { evidenceItemSchema } from '@/lib/api/reports';

it('retains original script, zero-width characters and line breaks as source text', () => {
  const title = 'شرکت\u200cالف';
  const summary = 'كي\u200cي\nکِی\u200cی <script>source text</script>';
  const { container } = render(
    <EvidenceAnnex
      evidence={[
        {
          ...report.version.evidence[0]!,
          title,
          summary,
          title_en: 'Unverified English rendering',
        },
      ]}
      findings={[]}
      status="ready"
    />,
  );
  const originalTitle = [...container.querySelectorAll('[dir="auto"]')].find(
    (node) => node.textContent === title,
  );
  const originalSummary = [...container.querySelectorAll('[dir="auto"]')].find(
    (node) => node.textContent === summary,
  );
  expect(originalTitle).toHaveClass('whitespace-pre-wrap');
  expect(originalSummary).toHaveClass('whitespace-pre-wrap');
  expect(container.querySelector('script')).toBeNull();
});

it('keeps translation and transliteration separate and displays date-only conversion without a false UTC instant', () => {
  const item = evidenceItemSchema.parse({
    ...report.version.evidence[0]!,
    published_at: null,
    transformations: ['translation', 'transliteration'].map((kind) => ({
      field: 'title',
      original_text: 'شرکت\u200cالف',
      transformed_text: kind === 'translation' ? 'Company A' : 'Sherkat-e Alef',
      kind,
      source_language: 'fa',
      target_language: 'en',
      source_script: 'Arab',
      target_script: 'Latn',
      origin: 'operator',
      method: 'Declared convention',
      model: 'recorded-model',
      provider: 'recorded-provider',
      profile_id: 'recorded-profile',
      review_status: 'operator_declared',
      limitations: ['Meaning unverified.'],
    })),
    source_dates: [
      {
        field: 'summary',
        raw_text: '۱۴۰۴-۰۱-۰۱',
        role: 'publication',
        calendar: 'solar_hijri_icu33',
        basis: 'operator',
        precision: 'day',
        status: 'resolved',
        method: 'ase-source-date-v1:solar_hijri_icu33',
        value: null,
        day_start: '2025-03-21',
        day_end: '2025-03-22',
        limitations: ['Timezone unknown.'],
      },
      {
        field: 'summary',
        raw_text: '01/02/1404',
        role: 'record_validity',
        calendar: 'unknown',
        basis: 'operator',
        precision: 'unknown',
        status: 'unsupported',
        method: 'ase-source-date-v1:unknown',
        limitations: ['Calendar undeclared.'],
      },
    ],
  });
  render(<EvidenceAnnex evidence={[item]} findings={[]} status="ready" />);
  expect(screen.getByText('translation of original title')).toBeInTheDocument();
  expect(screen.getByText('transliteration of original title')).toBeInTheDocument();
  expect(screen.getByText('۱۴۰۴-۰۱-۰۱')).toBeInTheDocument();
  expect(screen.getByText(/2025-03-21 to 2025-03-22/)).toHaveTextContent('Date precision only');
  expect(screen.getByText('unsupported / unknown')).toBeInTheDocument();
  expect(screen.queryByText('Resolved instant (explicit offset)')).not.toBeInTheDocument();
  expect(screen.getAllByText('recorded-provider / recorded-model / recorded-profile')).toHaveLength(
    2,
  );
  expect(item.transformations[0]?.original_text).toBe('شرکت\u200cالف');
});

it('renders recorded instant offsets and declarers without borrowing capture or current connection metadata', () => {
  const date = sourceDateSchema.parse({
    field: 'updated',
    raw_text: '2026-09-07T10:00:00+03:00',
    role: 'modification',
    calendar: 'gregorian',
    basis: 'source_spec',
    precision: 'instant',
    status: 'resolved',
    value: '2026-09-07T10:00:00+03:00',
    method: 'Source offset retained',
    actor_id: 'recorded-date-actor',
  });
  const transform = textTransformationSchema.parse({
    field: 'summary',
    original_text: 'Original',
    transformed_text: 'Rendering',
    kind: 'translation',
    source_language: 'und',
    target_language: 'en',
    origin: 'machine',
    method: 'Recorded method',
    review_status: 'unreviewed',
    actor_id: 'recorded-text-actor',
  });
  render(<SourceProvenanceDetails transformations={[transform]} dates={[date]} />);
  expect(screen.getByText('Declared source date: modification')).toBeVisible();
  expect(screen.getByText('Date declared by')).toBeVisible();
  expect(screen.getByText('recorded-date-actor')).toBeVisible();
  expect(screen.getByText('recorded-text-actor')).toBeVisible();
  expect(screen.getByText('Unreviewed')).toBeVisible();
  expect(screen.getByText('Resolved instant (explicit offset)')).toBeVisible();
  expect(screen.queryByText('Recorded translation connection')).not.toBeInTheDocument();
});

it('retains an unspecified source date without presenting it as publication', () => {
  const date = sourceDateSchema.parse({
    field: 'dc:date',
    raw_text: '2026-09-07',
    role: 'unspecified',
    calendar: 'gregorian',
    basis: 'source_metadata',
    precision: 'day',
    status: 'resolved',
    day_start: '2026-09-07',
    day_end: '2026-09-08',
    method: 'Declared Gregorian date',
  });
  render(<SourceProvenanceDetails dates={[date]} />);
  expect(screen.getByText('Declared source date: unspecified')).toBeVisible();
  expect(screen.queryByText('Declared source date: publication')).not.toBeInTheDocument();
});
