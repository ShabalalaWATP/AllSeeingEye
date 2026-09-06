import { describe, expect, it, vi } from 'vitest';

import * as profileApi from '@/lib/api/profile';
import { plainUser, tokenFor } from '@/test/fixtures';
import { defaultProfile } from '@/test/handlers.profile';

import { useAuthStore } from './auth';
import { useProfileStore } from './profile';

describe('identity-scoped preferences', () => {
  it('discards a late profile response after sign-out', async () => {
    let release: (value: profileApi.Profile) => void = () => undefined;
    const pending = new Promise<profileApi.Profile>((resolve) => {
      release = resolve;
    });
    vi.spyOn(profileApi, 'fetchProfile').mockReturnValueOnce(pending);
    useAuthStore.getState().setSession(tokenFor(plainUser));
    const load = useProfileStore.getState().reload();
    expect(useProfileStore.getState().loading).toBe(true);
    useAuthStore.getState().clearSession();
    release(defaultProfile);
    await load;
    expect(useProfileStore.getState().profile).toBeNull();
    expect(useProfileStore.getState().owner).toBeNull();
  });

  it('discards a late save after the same account signs out and back in', async () => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    await useProfileStore.getState().reload();
    let release: (value: profileApi.Profile) => void = () => undefined;
    const pending = new Promise<profileApi.Profile>((resolve) => {
      release = resolve;
    });
    vi.spyOn(profileApi, 'updateProfile').mockReturnValueOnce(pending);
    const save = useProfileStore.getState().save({ display_name: 'Earlier update' });
    useAuthStore.getState().clearSession();
    useAuthStore.getState().setSession(tokenFor(plainUser));
    release({ ...defaultProfile, display_name: 'Earlier update' });
    expect(await save).toBeNull();
    expect(useAuthStore.getState().user?.display_name).toBe(plainUser.display_name);
    expect(useProfileStore.getState().profile).toBeNull();
  });

  it('does not load or save without a signed-in account', async () => {
    useAuthStore.getState().clearSession();
    const get = vi.spyOn(profileApi, 'fetchProfile');
    const patch = vi.spyOn(profileApi, 'updateProfile');
    await useProfileStore.getState().reload();
    expect(await useProfileStore.getState().save({ timezone: 'UTC' })).toBeNull();
    expect(get).not.toHaveBeenCalled();
    expect(patch).not.toHaveBeenCalled();
  });
});
