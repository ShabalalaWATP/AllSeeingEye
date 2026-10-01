import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import { fetchReportJobs } from '@/lib/api/reportJobs';
import { fetchAlerts } from '@/lib/api/warning';
import { useAuthStore } from '@/stores/auth';
import { setVisibility } from '@/test/env';
import { plainUser, tokenFor } from '@/test/fixtures';

import { useNotificationBell } from './useNotificationBell';

vi.mock('@/lib/api/warning', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/api/warning')>()),
  fetchAlerts: vi.fn(() => new Promise(() => undefined)),
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
  vi.mocked(fetchAlerts).mockClear();
  vi.mocked(fetchReportJobs).mockClear();
});

it('forwards an abort signal to both shell fetchers and aborts it on clean-up', () => {
  const view = renderHook(() => useNotificationBell(plainUser.id));
  const alertSignal = vi.mocked(fetchAlerts).mock.calls[0]?.[1];
  const jobSignal = vi.mocked(fetchReportJobs).mock.calls[0]?.[0];
  expect(vi.mocked(fetchAlerts).mock.calls[0]?.[0]).toBe(24);
  expect(alertSignal).toBeInstanceOf(AbortSignal);
  expect(jobSignal).toBeInstanceOf(AbortSignal);
  expect(alertSignal?.aborted).toBe(false);
  expect(jobSignal?.aborted).toBe(false);
  view.unmount();
  expect(alertSignal?.aborted).toBe(true);
  expect(jobSignal?.aborted).toBe(true);
});
