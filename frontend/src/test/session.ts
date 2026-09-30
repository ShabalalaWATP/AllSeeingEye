import { useAuthStore } from '@/stores/auth';

import { adminUser, plainUser, tokenFor } from './fixtures';

export type Session = 'unknown' | 'anonymous' | 'user' | 'admin';

export function applySession(session: Session): void {
  const store = useAuthStore.getState();
  if (session === 'admin') store.setSession(tokenFor(adminUser));
  else if (session === 'user') store.setSession(tokenFor(plainUser));
  else if (session === 'anonymous') store.clearSession();
}
