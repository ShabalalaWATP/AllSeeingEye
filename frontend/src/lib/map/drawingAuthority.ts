/** Include role and activity so local map data is cleared even before an access event arrives. */
import type { AuthState } from '@/stores/auth';
export function drawingAuthority({ user, status }: Pick<AuthState, 'user' | 'status'>): string {
  return `${status}:${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}`;
}
