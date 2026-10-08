import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import { pushSupported } from '@/lib/browserPush';
import { renewPush } from '@/lib/pushRenewal';

import { usePushRenewal } from './usePushRenewal';

vi.mock('@/lib/browserPush', () => ({ pushSupported: vi.fn() }));
vi.mock('@/lib/pushRenewal', () => ({
  PUSH_CHANGED_MESSAGE: 'push-subscription-changed',
  renewPush: vi.fn(),
}));

const worker = new EventTarget();
beforeEach(() => {
  vi.mocked(pushSupported).mockReset().mockReturnValue(true);
  vi.mocked(renewPush).mockReset().mockResolvedValue(false);
  vi.stubGlobal('navigator', { serviceWorker: worker });
});
afterEach(() => {
  vi.unstubAllGlobals();
});

const message = (data: unknown) => worker.dispatchEvent(new MessageEvent('message', { data }));

it('renews for the signed-in account on load and when the worker reports a change', () => {
  const { unmount } = renderHook(() => usePushRenewal('user-a'));
  expect(renewPush).toHaveBeenCalledWith('user-a');
  message({ type: 'push-subscription-changed' });
  expect(renewPush).toHaveBeenCalledTimes(2);
  message({ type: 'something-else' });
  message(null);
  expect(renewPush).toHaveBeenCalledTimes(2);
  unmount();
  message({ type: 'push-subscription-changed' });
  expect(renewPush).toHaveBeenCalledTimes(2);
});

it('waits for a signed-in account and a browser that supports push', () => {
  const { rerender } = renderHook(({ owner }) => usePushRenewal(owner), {
    initialProps: { owner: null as string | null },
  });
  expect(renewPush).not.toHaveBeenCalled();
  vi.mocked(pushSupported).mockReturnValue(false);
  rerender({ owner: 'user-a' });
  expect(renewPush).not.toHaveBeenCalled();
});

it('keeps a failed renewal quiet, so the next load tries again', async () => {
  vi.mocked(renewPush).mockRejectedValue(new Error('Offline'));
  renderHook(() => usePushRenewal('user-a'));
  await Promise.resolve();
  expect(renewPush).toHaveBeenCalledOnce();
});
