import { apiSend } from './client';
import type { components } from './types.gen';

export type ChangePasswordInput = components['schemas']['ChangePasswordIn'];

/** Changing a password ends every session, including the authenticated caller. */
export function changePassword(body: ChangePasswordInput): Promise<void> {
  return apiSend('/api/me/password', { method: 'POST', body });
}
