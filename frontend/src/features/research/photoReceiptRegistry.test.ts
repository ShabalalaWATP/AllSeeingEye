import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { invalidateWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { photoId, photoReceipt } from '@/test/photoGeolocationFixture';

import {
  forgetPhotoReceipt,
  holdPhotoReceipt,
  outstandingPhotoReceipts,
  rememberPhotoReceipt,
} from './photoReceiptRegistry';

function key() {
  const user = useAuthStore.getState().user;
  return `${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}:${workspaceRevision()}`;
}

describe('bounded private photo receipt references', () => {
  beforeEach(() => useAuthStore.getState().setSession(tokenFor(plainUser)));
  afterEach(() => vi.useRealTimers());

  it('stores only valid unexpired references once, with a defensive bound', () => {
    const owner = key();
    const receipt = photoReceipt();
    rememberPhotoReceipt(owner, receipt);
    rememberPhotoReceipt(owner, receipt);
    rememberPhotoReceipt(
      owner,
      photoReceipt({ id: 'expired', expires_at: new Date(Date.now() - 1).toISOString() }),
    );
    expect(outstandingPhotoReceipts(owner)).toEqual([photoId]);
    for (let index = 0; index < 20; index += 1)
      rememberPhotoReceipt(owner, photoReceipt({ id: `bounded-${index}` }));
    expect(outstandingPhotoReceipts(owner)).toHaveLength(8);
    expect(outstandingPhotoReceipts(owner)).not.toContain('expired');
  });

  it('does not expose or delete another access context and clears after membership invalidation', () => {
    const owner = key();
    rememberPhotoReceipt(owner, photoReceipt());
    expect(() => outstandingPhotoReceipts('other-user')).toThrow('Account access changed');
    rememberPhotoReceipt('other-user', photoReceipt({ id: 'foreign' }));
    forgetPhotoReceipt('other-user', photoId);
    holdPhotoReceipt('other-user', photoReceipt())();
    expect(outstandingPhotoReceipts(owner)).toEqual([photoId]);
    invalidateWorkspaceAccess();
    expect(() => outstandingPhotoReceipts(owner)).toThrow('Account access changed');
    expect(outstandingPhotoReceipts(key())).toEqual([]);
  });

  it('does not retain receipt IDs for a signed-out account', () => {
    useAuthStore.getState().clearSession();
    rememberPhotoReceipt(key(), photoReceipt());
    expect(() => outstandingPhotoReceipts(key())).toThrow('Account access changed');
    holdPhotoReceipt(key(), photoReceipt())();
    useAuthStore.getState().setSession(tokenFor(plainUser));
    expect(outstandingPhotoReceipts(key())).toEqual([]);
  });

  it('holds an expired input until all reports settle, with idempotent release', () => {
    vi.useFakeTimers();
    const owner = key();
    const receipt = photoReceipt({ expires_at: new Date(Date.now() + 1000).toISOString() });
    const releaseFirst = holdPhotoReceipt(owner, receipt);
    const releaseSecond = holdPhotoReceipt(owner, receipt);
    vi.advanceTimersByTime(1001);
    releaseFirst();
    releaseFirst();
    expect(() => outstandingPhotoReceipts(owner)).toThrow('A photo report is still finishing');
    releaseSecond();
    expect(outstandingPhotoReceipts(owner)).toEqual([]);
  });
});
