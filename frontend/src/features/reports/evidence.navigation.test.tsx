import { fireEvent, render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { report, reportSummary } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { EvidenceAnnex } from './EvidenceAnnex';
import { EvidenceNavigation, Labels } from './EvidenceLinks';
import { ReportReviewStatus } from './ReportReviewStatus';

describe('report evidence navigation and review meaning', () => {
  it('prevents native fragment navigation from overriding disclosure focus, preserving modified links', () => {
    render(
      <EvidenceNavigation evidence={report.version.evidence}>
        <Labels labels={['E1']} />
        <EvidenceAnnex evidence={report.version.evidence} findings={[]} status="ready" />
      </EvidenceNavigation>,
    );
    const link = screen.getByRole('link', { name: 'View evidence E1' });
    const summary = screen.getByText('Shelling in Kharkiv').closest('summary');
    expect(fireEvent.click(link, { ctrlKey: true })).toBe(true);
    expect(summary?.parentElement).not.toHaveAttribute('open');
    expect(fireEvent.click(link)).toBe(false);
    expect(summary).toHaveFocus();
    expect(summary?.parentElement).toHaveAttribute('open');
  });

  it('opens and focuses cited evidence using an anchored keyboard link', async () => {
    const user = userEvent.setup();
    render(
      <EvidenceNavigation evidence={report.version.evidence}>
        <Labels labels={['E1', 'E1', 'unknown']} />
        <EvidenceAnnex evidence={report.version.evidence} findings={[]} status="ready" />
      </EvidenceNavigation>,
    );
    const link = screen.getByRole('link', { name: 'View evidence E1' });
    expect(link).toHaveAttribute('href', '#evidence-E1');
    expect(screen.queryByRole('link', { name: 'View evidence unknown' })).not.toBeInTheDocument();
    link.focus();
    await user.keyboard('{Enter}');
    const summary = screen.getByText('Shelling in Kharkiv').closest('summary');
    expect(summary).toHaveFocus();
    expect(summary?.parentElement).toHaveAttribute('open');
    expect(screen.getByText('Overnight shelling.')).toBeVisible();
  });

  it('does not throw when a cited disclosure is not mounted', async () => {
    const user = userEvent.setup();
    render(
      <EvidenceNavigation evidence={report.version.evidence}>
        <Labels labels={['E1']} />
      </EvidenceNavigation>,
    );
    await user.click(screen.getByRole('link', { name: 'View evidence E1' }));
    expect(screen.getByRole('link', { name: 'View evidence E1' })).toBeInTheDocument();
  });

  it('does not render an empty citation placeholder', () => {
    const { container } = render(<Labels labels={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it.each([
    ['ready', 'Automated checks passed'],
    ['needs_review', 'Review required'],
    ['failed', 'Generation failed'],
  ] as const)('explains the %s status without claiming human approval', (status, title) => {
    render(<ReportReviewStatus status={status} />);
    expect(screen.getByText(title)).toBeInTheDocument();
    if (status === 'ready')
      expect(
        screen.getByText(/does not establish factual accuracy or analyst verification/),
      ).toBeInTheDocument();
  });

  it('loads a saved version with its own period and hides technical generation detail initially', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.get('/api/reports/:id', async () => {
        await gate;
        return HttpResponse.json({
          ...report,
          version: {
            ...report.version,
            period_from: '2026-08-01T00:00:00Z',
            period_to: '2026-08-02T00:00:00Z',
            data_cutoff: '2026-08-02T01:00:00Z',
          },
        });
      }),
    );
    const { user } = renderApp(`/reports/${reportSummary.id}`, 'user');
    expect(await screen.findByText('Loading report')).toBeInTheDocument();
    release();
    await screen.findByText('Automated checks passed');
    expect(screen.getByText(/1 Aug 2026/)).toHaveTextContent('2 Aug 2026');
    expect(screen.queryByText(/3 Sept 2026/)).not.toBeInTheDocument();
    expect(screen.queryByText('Generation details')).not.toBeInTheDocument();
    const region = screen.getByRole('region', { name: 'Executive summary' });
    await user.click(within(region).getByRole('link', { name: 'View evidence E1' }));
    expect(screen.getByText('Overnight shelling.')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Sources & methods' }));
    await user.click(await screen.findByRole('button', { name: 'Review' }));
    await user.click(screen.getByText('Generation details'));
    expect(screen.getByText(/Data cut-off:/)).toHaveTextContent('2 Aug 2026, 01:00 UTC');
  });

  it('labels a legacy missing period without borrowing the current report dates', async () => {
    renderApp(`/reports/${reportSummary.id}`, 'user');
    expect(
      await screen.findByText(/Unknown for this legacy version/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/3 Sept 2026/)).not.toBeInTheDocument();
  });

  it('shows unavailable generation accounting explicitly on a failed historical version', async () => {
    server.use(
      http.get('/api/reports/:id', () =>
        HttpResponse.json({
          ...report,
          version: {
            ...report.version,
            status: 'failed',
            attempts: 2,
            prompt_tokens: null,
            completion_tokens: null,
          },
        }),
      ),
    );
    const { user } = renderApp(`/reports/${reportSummary.id}`, 'user');
    await screen.findByText('Generation failed');
    await user.click(screen.getByRole('button', { name: 'Sources & methods' }));
    await user.click(await screen.findByRole('button', { name: 'Review' }));
    await user.click(screen.getByText('Generation details'));
    expect(screen.getByText(/Unknown input/)).toHaveTextContent('2 attempts');
    expect(screen.getByText(/Unknown input/)).toHaveTextContent('Unknown output tokens');
    expect(screen.getByText(/Data cut-off:/)).toHaveTextContent('Unknown');
  });
});
