import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import { readResearchProgress, type ResearchRunReceipt } from '@/lib/api/researchProgress';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';

import { ResearchProgress } from './ResearchProgress';
import { useResearchProgress } from './useResearchProgress';

vi.mock('@/lib/api/researchProgress', () => ({ readResearchProgress: vi.fn() }));
const read = vi.mocked(readResearchProgress);
const id = '10000000-0000-4000-8000-000000000001';
function receipt(stage: ResearchRunReceipt['stage'] = 'collecting'): ResearchRunReceipt {
  return {
    id,
    stage,
    started_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 900_000).toISOString(),
    report_id: null,
  };
}
async function tick(ms = 2000) {
  await act(() => vi.advanceTimersByTimeAsync(ms));
}

describe('research progress lifecycle', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(crypto, 'randomUUID').mockReturnValue(id);
    read.mockReset();
    useAuthStore.getState().setSession(tokenFor(plainUser));
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('starts without invented progress, tolerates initial 404 and uses actual server stages', async () => {
    read
      .mockRejectedValueOnce(new ApiError(404, 'not_found', 'Not found'))
      .mockResolvedValueOnce(receipt('drafting'))
      .mockResolvedValueOnce(receipt('completed'));
    const { result } = renderHook(useResearchProgress);
    let options!: ReturnType<typeof result.current.begin>;
    act(() => {
      options = result.current.begin();
    });
    expect(options.runId).toBe(id);
    expect(options.signal.aborted).toBe(false);
    expect(result.current.snapshot).toEqual({
      stage: null,
      outcome: 'running',
      unavailable: false,
    });
    expect(read).not.toHaveBeenCalled();
    await tick();
    expect(result.current.snapshot?.unavailable).toBe(false);
    await tick();
    expect(result.current.snapshot?.stage).toBe('drafting');
    await tick();
    expect(result.current.snapshot?.stage).toBe('completed');
    await tick(10_000);
    expect(read).toHaveBeenCalledTimes(3);
    act(() => result.current.finish('failed'));
    expect(result.current.snapshot?.outcome).toBe('completed');
  });

  it('shows unavailable after a registered receipt disappears, then recovers', async () => {
    read
      .mockResolvedValueOnce(receipt())
      .mockRejectedValueOnce(new ApiError(404, 'not_found', 'Gone'))
      .mockResolvedValueOnce(receipt('saving'));
    const { result } = renderHook(useResearchProgress);
    act(() => {
      result.current.begin();
    });
    await tick();
    await tick();
    expect(result.current.snapshot?.unavailable).toBe(true);
    await tick();
    expect(result.current.snapshot).toMatchObject({ stage: 'saving', unavailable: false });
  });

  it('does not overlap slow polls and cancellation aborts both request and status fetch', async () => {
    let resolve!: (value: ResearchRunReceipt) => void;
    read.mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    const { result } = renderHook(useResearchProgress);
    let signal!: AbortSignal;
    act(() => {
      signal = result.current.begin().signal;
    });
    await tick(10_000);
    expect(read).toHaveBeenCalledTimes(1);
    const pollSignal = read.mock.calls[0]?.[1];
    act(() => result.current.cancel());
    expect(signal.aborted).toBe(true);
    expect(pollSignal?.aborted).toBe(true);
    await act(async () => {
      resolve(receipt('completed'));
      await Promise.resolve();
    });
    act(() => result.current.finish('failed'));
    expect(result.current.snapshot?.outcome).toBe('cancelled');
    expect(result.current.active).toBe(false);
    await tick(10_000);
    expect(read).toHaveBeenCalledTimes(1);
  });

  it.each(['account', 'workspace', 'logout'] as const)(
    'aborts and hides on %s change, including return to old account',
    async (change) => {
      read.mockResolvedValue(receipt());
      const { result } = renderHook(useResearchProgress);
      let signal!: AbortSignal;
      act(() => {
        signal = result.current.begin().signal;
      });
      await tick();
      act(() => {
        if (change === 'workspace') invalidateWorkspaceAccess();
        else if (change === 'logout') useAuthStore.getState().clearSession();
        else useAuthStore.getState().setSession(tokenFor(adminUser));
      });
      expect(signal.aborted).toBe(true);
      expect(result.current.snapshot).toBeNull();
      act(() => useAuthStore.getState().setSession(tokenFor(plainUser)));
      expect(result.current.snapshot).toBeNull();
      await tick();
      expect(read).toHaveBeenCalledTimes(1);
    },
  );

  it('aborts on unmount and ignores a late failed poll', async () => {
    let reject!: (reason: Error) => void;
    read.mockReturnValue(
      new Promise((_resolve, fail) => {
        reject = fail;
      }),
    );
    const { result, unmount } = renderHook(useResearchProgress);
    let signal!: AbortSignal;
    act(() => {
      signal = result.current.begin().signal;
    });
    await tick();
    unmount();
    expect(signal.aborted).toBe(true);
    await act(async () => {
      reject(new Error('Late failure'));
      await Promise.resolve();
    });
    await tick();
    expect(read).toHaveBeenCalledTimes(1);
  });

  it('rejects mismatched receipts and bounds polling to the receipt expiry', async () => {
    read
      .mockResolvedValueOnce({ ...receipt(), id: '20000000-0000-4000-8000-000000000001' })
      .mockResolvedValueOnce({
        ...receipt(),
        expires_at: new Date(Date.now() + 4500).toISOString(),
      });
    const { result } = renderHook(useResearchProgress);
    act(() => {
      result.current.begin();
    });
    await tick();
    expect(result.current.snapshot?.unavailable).toBe(true);
    await tick();
    await tick();
    await tick(20_000);
    expect(read).toHaveBeenCalledTimes(2);
    expect(result.current.snapshot?.unavailable).toBe(true);
  });

  it.each(['completed', 'failed', 'cancelled'] as const)(
    'ends polling after %s request result',
    async (outcome) => {
      const { result } = renderHook(useResearchProgress);
      act(() => {
        result.current.finish(outcome);
        result.current.cancel();
        result.current.begin();
      });
      act(() => result.current.finish(outcome));
      await tick();
      expect(read).not.toHaveBeenCalled();
      expect(result.current.snapshot?.outcome).toBe(outcome);
    },
  );

  it('a replacement request aborts the old request and clears its stage', async () => {
    read.mockResolvedValue(receipt('challenging'));
    const { result } = renderHook(useResearchProgress);
    let signal!: AbortSignal;
    act(() => {
      signal = result.current.begin().signal;
    });
    await tick();
    act(() => {
      result.current.begin();
    });
    expect(signal.aborted).toBe(true);
    expect(result.current.snapshot?.stage).toBeNull();
  });
});

describe('research progress display', () => {
  it.each([
    ['running', 'Starting research'],
    ['completed', 'Report saved'],
  ] as const)('shows %s without claiming an unreported server stage', (outcome, title) => {
    render(
      <ResearchProgress
        snapshot={{ stage: null, outcome, unavailable: false }}
        active={false}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByRole('status')).toHaveTextContent(title);
  });
  it('renders nothing before a run', () => {
    const { container } = render(
      <ResearchProgress snapshot={null} active={false} onCancel={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
  it('names the real stage, exposes cancellation and does not render a percentage', () => {
    const cancel = vi.fn();
    render(
      <ResearchProgress
        snapshot={{ stage: 'validating', outcome: 'running', unavailable: true }}
        active
        onCancel={cancel}
      />,
    );
    expect(screen.getByRole('status')).toHaveTextContent('Checking the report');
    expect(screen.getByText(/Live progress is unavailable/)).toBeVisible();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel research' }));
    expect(cancel).toHaveBeenCalledOnce();
  });
  it.each(['cancelled', 'failed'] as const)('explains uncertain saving after %s', (outcome) => {
    render(
      <MemoryRouter>
        <ResearchProgress
          snapshot={{ stage: 'saving', outcome, unavailable: false }}
          active={false}
          onCancel={vi.fn()}
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: 'Check Reports' })).toHaveAttribute('href', '/reports');
    expect(screen.getByText(/A report being saved may still complete/)).toBeVisible();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
