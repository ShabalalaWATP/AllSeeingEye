import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { applySession } from '@/test/render';
import { secReceipt } from '@/test/fixtures.secFilings';
import type { InputDeclarations } from '@/lib/api/inputDeclarations';
import { InputProvenanceDeclarations } from './InputProvenanceDeclarations';

it.each(['date', 'transformation'] as const)(
  'counts retained source %s rows before saving and allows the remaining capacity',
  async (kind) => {
    applySession('user');
    const receipt = secReceipt();
    const saved = vi.fn<(body: InputDeclarations) => void>();
    const onReplace = vi.fn();
    const sourceDate = {
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
    const transformation = {
      field: 'title',
      original_text: 'Source 2026-01-01',
      transformed_text: 'Source rendering',
      kind: 'translation',
      source_language: 'en',
      target_language: 'de',
      origin: 'source',
      method: 'Source supplied',
      review_status: 'unreviewed',
      limitations: [],
    };
    server.use(
      http.get('/api/research/inputs/:id/declaration-targets', () =>
        HttpResponse.json({
          input_id: receipt.id,
          sha256: receipt.sha256,
          expires_at: receipt.expires_at,
          targets: [
            {
              event_id: 'passage',
              content_hash: 'b'.repeat(64),
              title: 'Source 2026-01-01',
              summary: null,
              language: 'en',
              source_dates: kind === 'date' ? [sourceDate] : [],
              transformations: kind === 'transformation' ? [transformation] : [],
            },
          ],
        }),
      ),
      http.post('/api/research/inputs/:id/declarations', async ({ request }) => {
        saved((await request.json()) as InputDeclarations);
        return HttpResponse.json({
          ...receipt,
          id: '20000000-0000-4000-8000-000000000003',
          parent_input_id: receipt.id,
        });
      }),
    );
    render(
      <InputProvenanceDeclarations
        receipt={receipt}
        disabled={false}
        onReplace={onReplace}
        onBusy={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByText('Declare source language or calendar'));
    await userEvent.click(screen.getByRole('button', { name: 'Load original passages' }));
    await screen.findByText(/Recorded provenance, read-only/);
    for (let index = 1; index <= 4; index++) {
      await userEvent.click(screen.getByRole('button', { name: 'Add passage declaration' }));
      await userEvent.selectOptions(
        screen.getByLabelText(`Declaration ${index} passage`),
        'passage',
      );
      if (kind === 'date') {
        await userEvent.click(screen.getByLabelText(`Declaration ${index}: declare a source date`));
        fireEvent.change(screen.getByLabelText(`Declaration ${index} raw source date`), {
          target: { value: '2026-01-01' },
        });
      } else {
        await userEvent.click(
          screen.getByLabelText(`Declaration ${index}: supply text transformation`),
        );
        fireEvent.change(screen.getByLabelText(`Declaration ${index} transformed text`), {
          target: { value: `Rendering ${index}` },
        });
        fireEvent.change(screen.getByLabelText(`Declaration ${index} method`), {
          target: { value: 'Operator rendering' },
        });
      }
    }
    await userEvent.click(
      screen.getByRole('button', { name: 'Save declarations for this research' }),
    );
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'including retained source metadata',
    );
    expect(saved).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Remove declaration 4' }));
    await userEvent.click(
      screen.getByRole('button', { name: 'Save declarations for this research' }),
    );
    await screen.findByRole('button', { name: 'Refresh original passages' });
    expect(saved).toHaveBeenCalledOnce();
    const body = saved.mock.calls[0]![0];
    expect(body.declarations).toHaveLength(1);
    expect(body.declarations[0]![kind === 'date' ? 'source_dates' : 'transformations']).toHaveLength(
      3,
    );
    expect(JSON.stringify(body)).not.toContain(kind === 'date' ? 'source_spec' : 'Source supplied');
  },
);
