import { reportJob, readReportJobRequest } from '@/test/reportJobFixture';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { server } from '@/test/server';
import { renderApp } from '@/test/render';
import { report } from '@/test/fixtures';
import { secChoice, secPage, secReceipt } from '@/test/fixtures.secFilings';
import type { InputDeclarations } from '@/lib/api/inputDeclarations';
import type { ReportRequest } from '@/lib/api/reports';
import type { SourceDate } from '@/lib/api/sourceProvenance';
import '@/features/research/ResearchPage';
import '@/features/reports/ReportPage';

const original = 'Company statement 1404-01-01';
const sourceDate: SourceDate = {
  field: 'filingDate',
  raw_text: '2026-01-01',
  role: 'publication',
  calendar: 'gregorian',
  basis: 'source_spec',
  precision: 'day',
  status: 'resolved',
  day_start: '2026-01-01',
  day_end: '2026-01-02',
  method: 'SEC filingDate',
  limitations: [],
};
const operatorDate: SourceDate = {
  field: 'title',
  raw_text: '1404-01-01',
  role: 'occurrence',
  calendar: 'solar_hijri_icu33',
  basis: 'operator',
  precision: 'day',
  status: 'resolved',
  day_start: '2025-03-21',
  day_end: '2025-03-22',
  method: 'ICU33 arithmetic',
  limitations: [],
};

it.each(['sec', 'local'] as const)(
  'carries %s import declarations through the selected input ID to report evidence',
  async (method) => {
    const receipt = secReceipt({ filename: method === 'sec' ? 'filing.htm' : 'notes.txt' });
    const derived = {
      ...receipt,
      id: '20000000-0000-4000-8000-000000000003',
      parent_input_id: receipt.id,
    };
    const requests: ReportRequest[] = [];
    const declarations: InputDeclarations[] = [];
    const sourceDates = method === 'sec' ? [sourceDate] : [];
    const completed = {
      ...report,
      version: {
        ...report.version,
        evidence: [
          {
            ...report.version.evidence[0]!,
            title: original,
            published_at: null,
            captured_at: receipt.imported_at,
            source_dates: [...sourceDates, operatorDate],
            transformations: [
              {
                field: 'title',
                original_text: original,
                transformed_text: 'Declared rendering',
                kind: 'transliteration',
                source_language: 'und',
                target_language: 'und',
                origin: 'operator',
                method: 'Operator convention',
                review_status: 'operator_declared',
                limitations: [],
              },
            ],
          },
        ],
      },
    };
    server.use(
      http.post('/api/research/sec/filings', () => HttpResponse.json(secPage())),
      http.post('/api/research/sec/filings/:id/import', () =>
        HttpResponse.json(receipt, { status: 201 }),
      ),
      http.post('/api/research/inputs', () => HttpResponse.json(receipt, { status: 201 })),
      http.get('/api/research/inputs/:id/declaration-targets', ({ params }) =>
        HttpResponse.json({
          input_id: params.id,
          sha256: receipt.sha256,
          expires_at: receipt.expires_at,
          targets: [
            {
              event_id: 'passage',
              content_hash: 'b'.repeat(64),
              title: original,
              summary: 'Original source snippet',
              language: 'und',
              transformations: [],
              source_dates: sourceDates,
            },
          ],
        }),
      ),
      http.post('/api/research/inputs/:id/declarations', async ({ request, params }) => {
        expect(params.id).toBe(receipt.id);
        declarations.push((await request.json()) as InputDeclarations);
        return HttpResponse.json(derived, { status: 201 });
      }),
      http.post('/api/report-jobs', async ({ request }) => {
        requests.push(await readReportJobRequest(request));
        return HttpResponse.json(reportJob({ status: 'completed', report_id: report.report.id }), {
          status: 202,
        });
      }),
      http.get(`/api/reports/${report.report.id}`, () => HttpResponse.json(completed)),
      http.get('/api/report-jobs/:id', () =>
        HttpResponse.json(reportJob({ status: 'completed', report_id: report.report.id })),
      ),
    );
    renderApp('/research?question=Analyse%20this%20document', 'user');
    await screen.findByLabelText('Research focus');
    await userEvent.click(screen.getByText('Scope and sources'));
    await userEvent.selectOptions(screen.getByLabelText('Research focus'), 'document');
    if (method === 'sec') {
      await userEvent.click(screen.getByRole('button', { name: 'Find an SEC filing' }));
      fireEvent.change(screen.getByLabelText('SEC company identifier (CIK)'), {
        target: { value: '320193' },
      });
      await userEvent.click(screen.getByRole('button', { name: 'Discover SEC filings' }));
      await userEvent.click(
        await screen.findByRole('button', { name: `Import document ${secChoice().accession}` }),
      );
      await screen.findByRole('heading', { name: 'Attached filing document: filing.htm' });
    } else {
      fireEvent.change(screen.getByLabelText('Document or media'), {
        target: { files: [new File([original], 'notes.txt')] },
      });
      await screen.findByText('Attached: notes.txt');
    }
    await userEvent.click(screen.getByText('Declare source language or calendar'));
    await userEvent.click(screen.getByRole('button', { name: 'Load original passages' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Add passage declaration' }));
    if (method === 'sec') {
      expect(screen.getByText(/Recorded provenance, read-only/)).toBeInTheDocument();
      expect(screen.getByText('2026-01-01')).toBeInTheDocument();
    }
    await userEvent.selectOptions(screen.getByLabelText('Declaration 1 passage'), 'passage');
    await userEvent.click(screen.getByLabelText('Declaration 1: supply text transformation'));
    fireEvent.change(screen.getByLabelText('Declaration 1 transformed text'), {
      target: { value: 'Declared rendering' },
    });
    fireEvent.change(screen.getByLabelText('Declaration 1 method'), {
      target: { value: 'Operator convention' },
    });
    await userEvent.click(screen.getByLabelText('Declaration 1: declare a source date'));
    fireEvent.change(screen.getByLabelText('Declaration 1 raw source date'), {
      target: { value: '1404-01-01' },
    });
    await userEvent.selectOptions(
      screen.getByLabelText('Declaration 1 calendar'),
      'solar_hijri_icu33',
    );
    await userEvent.selectOptions(screen.getByLabelText('Declaration 1 date role'), 'occurrence');
    await userEvent.click(
      screen.getByRole('button', { name: 'Save declarations for this research' }),
    );
    await screen.findByText(/available for inspection only/);
    expect(declarations[0]?.declarations[0]).toMatchObject({
      event_id: 'passage',
      content_hash: 'b'.repeat(64),
      transformations: [{ original_text: original, kind: 'transliteration' }],
      source_dates: [{ raw_text: '1404-01-01', role: 'occurrence', calendar: 'solar_hijri_icu33' }],
    });
    expect(declarations[0]?.declarations[0]?.source_dates).toHaveLength(1);
    const start = screen.getByRole('button', { name: 'Start research' });
    await waitFor(() => expect(start).toBeEnabled());
    await userEvent.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() => expect(requests[0]?.research_input_id).toBe(derived.id));
    await userEvent.click(await screen.findByRole('link', { name: /Open completed report/ }));
    await userEvent.click(await screen.findByRole('button', { name: 'Sources & methods' }));
    const annex = await screen.findByRole('region', { name: 'Evidence annex' });
    await userEvent.click(within(annex).getAllByText(original)[0]!);
    expect(within(annex).getByText('Declared rendering')).toBeVisible();
    expect(within(annex).getByText('Published').parentElement).toHaveTextContent('Unknown');
    expect(within(annex).getByText('Captured').parentElement).not.toHaveTextContent('Unknown');
    if (method === 'sec') expect(within(annex).getByText('SEC filingDate')).toBeVisible();
    expect(within(annex).getByText('ICU33 arithmetic')).toBeVisible();
  },
);
