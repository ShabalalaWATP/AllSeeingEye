import { act, render } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { getFeedStatus, type FeedStatus } from '@/lib/api/notifications';
import { PrivateFeedSettings } from './PrivateFeedSettings';

vi.mock('@/lib/api/notifications', () => ({
  getFeedStatus: vi.fn(),
  enableFeed: vi.fn(),
  revokeFeed: vi.fn(),
}));

it.each(['success', 'failure'])(
  'aborts the feed request on navigation before a late %s',
  async (outcome) => {
    let finish!: (value: FeedStatus) => void;
    let fail!: (error: Error) => void;
    const pending = new Promise<FeedStatus>((resolve, reject) => {
      finish = resolve;
      fail = reject;
    });
    vi.mocked(getFeedStatus).mockReturnValueOnce(pending);
    const view = render(<PrivateFeedSettings />);
    const signal = vi.mocked(getFeedStatus).mock.lastCall?.[0];
    expect(signal?.aborted).toBe(false);
    view.unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      if (outcome === 'success')
        finish({ enabled: false, include_titles: false, created_at: null });
      else fail(new DOMException('Aborted', 'AbortError'));
      await pending.catch(() => undefined);
    });
  },
);
