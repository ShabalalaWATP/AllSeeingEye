/** Admin endpoints from docs/api/AUTH_API.md. All require the admin role. */
import { apiCall, apiSend } from './client';
import {
  accountRequestListSchema,
  approveResponseSchema,
  auditPageSchema,
  resetLinkResponseSchema,
  userListSchema,
  userSchema,
} from './schemas';
import type {
  AccountRequest,
  ApproveResponse,
  AuditPage,
  ResetLinkResponse,
  Role,
  User,
} from './schemas';

export const AUDIT_PAGE_SIZE = 100;

export async function listPendingAccountRequests(): Promise<AccountRequest[]> {
  const page = await apiCall('/api/admin/account-requests?status=pending', {
    schema: accountRequestListSchema,
  });
  return page.items;
}

export function approveAccountRequest(id: string, role: Role): Promise<ApproveResponse> {
  return apiCall(`/api/admin/account-requests/${encodeURIComponent(id)}/approve`, {
    method: 'POST',
    body: { role },
    schema: approveResponseSchema,
  });
}

export function rejectAccountRequest(id: string, reason?: string): Promise<void> {
  const body = reason === undefined || reason.trim() === '' ? {} : { reason: reason.trim() };
  return apiSend(`/api/admin/account-requests/${encodeURIComponent(id)}/reject`, {
    method: 'POST',
    body,
  });
}

export async function listUsers(): Promise<User[]> {
  const page = await apiCall('/api/admin/users', { schema: userListSchema });
  return page.items;
}

export interface UserPatch {
  role?: Role;
  is_active?: boolean;
}

export function updateUser(id: string, patch: UserPatch): Promise<User> {
  return apiCall(`/api/admin/users/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: patch,
    schema: userSchema,
  });
}

export function issueResetLink(id: string): Promise<ResetLinkResponse> {
  return apiCall(`/api/admin/users/${encodeURIComponent(id)}/reset-link`, {
    method: 'POST',
    schema: resetLinkResponseSchema,
  });
}

export function fetchAuditPage(before: number | null): Promise<AuditPage> {
  const params = new URLSearchParams({ limit: String(AUDIT_PAGE_SIZE) });
  if (before !== null) params.set('before', String(before));
  return apiCall(`/api/admin/audit-log?${params.toString()}`, { schema: auditPageSchema });
}
