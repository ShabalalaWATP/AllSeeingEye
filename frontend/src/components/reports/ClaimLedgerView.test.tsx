import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { ClaimLedger } from '@/lib/api/claimLedger';
import { reportAssessment } from '@/test/fixtures.reportAssessment';
import { ClaimLedgerView } from './ClaimLedgerView';

const ledger: ClaimLedger = {
  derivation_version: 'test',
  report_version: 3,
  recorded_gaps: ['Origin remains unknown.'],
  limitations: ['No truth score is calculated.'],
  claims: [
    {
      id: 'stable-version-claim',
      judgement_id: 'KJ1',
      statement: 'Units leave. The camp is empty.',
      kind: 'analytical_inference',
      confidence_statement: 'Evidence is limited.',
      assumptions: ['A1'],
      assessment: reportAssessment.judgements[0]!,
      citation_checks: {
        judgement_id: 'KJ1',
        status: 'review_required',
        reasons: [],
        citations: [
          {
            label: 'E1',
            relation: 'supporting',
            status: 'excerpt_present',
            evidence_id: 'one',
            source_content_hash: 'hash',
            indicators: [],
            reasons: ['Inspect context.'],
            excerpt: {
              field: 'summary',
              start: 0,
              end: 25,
              text: '<script>alert(1)</script>',
              sha256: 'hash',
            },
          },
        ],
      },
      sources: [
        {
          label: 'E1',
          relation: 'supporting',
          source_name: 'Frozen source',
          evidence_id: 'one',
          organisation: null,
          content_hash: 'hash',
        },
      ],
      dimensions: [
        { name: 'evidence_support', status: 'contested', explanation: 'Saved assessment.' },
        { name: 'source_independence', status: 'declared_only', explanation: 'No verified chain.' },
        { name: 'coverage', status: 'unknown', explanation: 'Completeness not measured.' },
        {
          name: 'citation_validity',
          status: 'review_required',
          explanation: 'Literal checks only.',
        },
      ],
    },
  ],
};

describe('claim inspection', () => {
  it('shows separate saved dimensions, source relationships and literal escaped excerpts', async () => {
    const { container } = render(<ClaimLedgerView ledger={ledger} />);
    await userEvent.click(screen.getByText(/KJ1 · Units leave/));
    for (const name of [
      'Evidence support',
      'Source independence',
      'Research coverage',
      'Citation validity',
    ])
      expect(screen.getByText(name)).toBeVisible();
    expect(screen.getByText('Evidence is limited.')).toBeVisible();
    expect(screen.getByText('<script>alert(1)</script>')).toBeVisible();
    expect(container.querySelector('script')).toBeNull();
    expect(screen.getByText(/Declared organisation: Unknown/)).toBeVisible();
    expect(screen.getByText(/supporting · Frozen source/)).toBeVisible();
    expect(screen.getByText(/Source groups|Saved source groups/)).toBeVisible();
  });

  it('handles missing metadata and empty versions without inventing findings', () => {
    const { rerender } = render(<ClaimLedgerView ledger={null} />);
    expect(screen.getByText('Claim inspection is unavailable for this response.')).toBeVisible();
    rerender(<ClaimLedgerView ledger={{ ...ledger, claims: [], recorded_gaps: [] }} />);
    expect(screen.getByText('No judgements were saved in this version.')).toBeVisible();
  });

  it('retains an unknown legacy judgement and missing evidence label', async () => {
    render(
      <ClaimLedgerView
        ledger={{
          ...ledger,
          claims: [
            {
              ...ledger.claims[0]!,
              assessment: null,
              citation_checks: null,
              confidence_statement: '',
              assumptions: [],
              sources: [
                {
                  label: 'E999',
                  relation: 'contradicting',
                  source_name: null,
                  evidence_id: null,
                  organisation: null,
                  content_hash: null,
                },
              ],
            },
          ],
        }}
      />,
    );
    await userEvent.click(screen.getByText(/KJ1 · Units leave/));
    expect(screen.getByText(/Frozen evidence missing/)).toBeVisible();
    expect(screen.getByText('No confidence explanation recorded.')).toBeVisible();
  });
});
