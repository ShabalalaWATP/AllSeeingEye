import type { AccountRequest, AuditEntry, TokenResponse, User } from '@/lib/api/schemas';

export const ADMIN_TOKEN = 'admin-access-token';
export const USER_TOKEN = 'user-access-token';
export const CSRF_VALUE = 'csrf-test-value';
export const ADMIN_PASSWORD = 'correct-horse-battery-staple';
export const USER_PASSWORD = 'another-long-passphrase';
export const ACTIVATION_LINK = 'http://localhost:3000/activate?token=activation-token-123';
export const RESET_LINK = 'http://localhost:3000/reset-password?token=reset-token-456';
export const GOOD_TOKEN = 'good-token';
export const BAD_TOKEN = 'bad-token';
export const WEAK_PASSWORD = 'password12345';
export const WEAK_PASSWORD_REASON = 'This password is among the most common and cannot be used.';

export const adminUser: User = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'admin@example.com',
  display_name: 'Ada Admin',
  role: 'admin',
  is_active: true,
  created_at: '2026-09-01T10:00:00Z',
  last_login_at: '2026-09-04T09:00:00Z',
};

export const plainUser: User = {
  id: '22222222-2222-4222-8222-222222222222',
  email: 'user@example.com',
  display_name: 'Uma User',
  role: 'user',
  is_active: true,
  created_at: '2026-09-02T10:00:00Z',
  last_login_at: null,
};

export function tokenFor(user: User): TokenResponse {
  return {
    access_token: user.role === 'admin' ? ADMIN_TOKEN : USER_TOKEN,
    token_type: 'bearer',
    expires_in: 900,
    user,
  };
}

export const pendingRequests: AccountRequest[] = [
  {
    id: '33333333-3333-4333-8333-333333333333',
    email: 'newcomer@example.com',
    display_name: 'Nia Newcomer',
    reason: 'Analyst on the regional desk.',
    status: 'pending',
    created_at: '2026-09-03T12:00:00Z',
  },
  {
    id: '44444444-4444-4444-8444-444444444444',
    email: 'second@example.com',
    display_name: 'Sam Second',
    reason: null,
    status: 'pending',
    created_at: '2026-09-03T13:00:00Z',
  },
];

export function auditEntry(id: number, action: string): AuditEntry {
  return {
    id,
    at: '2026-09-04T08:00:00Z',
    actor_user_id: adminUser.id,
    action,
    subject: 'user@example.com',
    ip: '127.0.0.1',
    details: id % 2 === 0 ? {} : { note: `entry ${id}` },
  };
}

export const auditPageOne: AuditEntry[] = [
  auditEntry(120, 'login_succeeded'),
  auditEntry(119, 'user_updated'),
  auditEntry(118, 'account_request_approved'),
];

export const auditPageTwo: AuditEntry[] = [auditEntry(50, 'logout'), auditEntry(49, 'login_failed')];
