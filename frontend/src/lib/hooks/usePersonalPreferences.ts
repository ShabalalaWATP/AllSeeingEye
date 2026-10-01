import { useAuthStore } from '@/stores/auth';
import { useProfileStore } from '@/stores/profile';

/** The signed-in account's own loaded preferences; never fetched here, never another account's. */
export function usePersonalPreferences() {
  const actorId = useAuthStore((state) => state.user?.id);
  return useProfileStore((state) =>
    actorId !== undefined && state.owner === actorId ? state.profile : null,
  );
}
