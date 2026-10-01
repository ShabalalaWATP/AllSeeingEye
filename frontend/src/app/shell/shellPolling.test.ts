import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import { fetchReportJobs } from '@/lib/api/reportJobs';
import { fetchBell } from '@/lib/api/bell';
import { useAuthStore } from '@/stores/auth';
import { setVisibility } from '@/test/env';
import { plainUser, tokenFor } from '@/test/fixtures';

import { useNotificationBell } from './useNotificationBell';

vi.mock('@/lib/api/bell', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/api/bell')>()),
  fetchBell: vi.fn(() => new Promise(() => undefined)),
}));
vi.mock('@/lib/api/reportJobs', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/api/reportJobs')>()),
  fetchReportJobs: vi.fn(() => new Promise(() => undefined)),
}));

beforeEach(() => {
  setVisibility('visible');
  useAuthStore.getState().setSession(tokenFor(plainUser));
});

afterEach(() => {
  vi.mocked(fetchBell).mockClear();
  vi.mocked(fetchReportJobs).mockClear();
});

it('forwards an abort signal to both shell fetchers and aborts it on clean-up', () => {
  const view = renderHook(() => useNotificationBell(plainUser.id));
  const alertSignal = vi.mocked(fetchBell).mock.calls[0]?.[0];
  const jobSignal = vi.mocked(fetchReportJobs).mock.calls[0]?.[0];
  expect(alertSignal).toBeInstanceOf(AbortSignal);
  expect(jobSignal).toBeInstanceOf(AbortSignal);
  expect(alertSignal?.aborted).toBe(false);
  expect(jobSignal?.aborted).toBe(false);
  view.unmount();
  expect(alertSignal?.aborted).toBe(true);
  expect(jobSignal?.aborted).toBe(true);
});
