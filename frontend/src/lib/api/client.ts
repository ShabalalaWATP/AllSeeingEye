/**
 * Fetch wrapper for the ASE API. Sends cookies, injects the bearer token, parses
 * the error envelope into ApiError, validates successful bodies with zod, and on
 * a 401 refreshes the session once and retries before giving up.
 *
 * The client never imports the auth store (lib must not depend on stores); the
 * store binds itself through `bindSession`.
 */
import type { ZodType } from 'zod';

import { ApiError } from './errors';
import { errorEnvelopeSchema } from './schemas';

export interface SessionBridge {
  getAccessToken(): string | null;
  /** Refreshes the session and resolves to the new access token, or null on failure. */
  refreshAccessToken(): Promise<string | null>;
  onSessionLost(): void;
}

const noSession: SessionBridge = {
  getAccessToken: () => null,
  refreshAccessToken: () => Promise.resolve(null),
  onSessionLost: () => undefined,
};

let session: SessionBridge = noSession;

export function bindSession(bridge: SessionBridge): void {
  session = bridge;
}

export function resetSessionBinding(): void {
  session = noSession;
}

export type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

export interface CallOptions {
  method?: HttpMethod;
  body?: unknown;
  headers?: Record<string, string>;
  /** When true (default) the bearer token is attached and a 401 triggers one refresh and retry. */
  auth?: boolean;
}

/** Performs a request whose successful body is validated against `schema`. */
export async function apiCall<T>(
  path: string,
  options: CallOptions & { schema: ZodType<T> },
): Promise<T> {
  const response = await execute(path, options);
  const data: unknown = await response.json();
  const parsed = options.schema.safeParse(data);
  if (!parsed.success) {
    throw new ApiError(
      response.status,
      'invalid_response',
      'The server sent an unexpected response.',
    );
  }
  return parsed.data;
}

/** Performs a request whose successful response has no body of interest (for example 204). */
export async function apiSend(path: string, options: CallOptions = {}): Promise<void> {
  await execute(path, options);
}

async function execute(path: string, options: CallOptions): Promise<Response> {
  const auth = options.auth ?? true;
  const first = await send(path, options, auth ? session.getAccessToken() : null);
  if (first.status !== 401 || !auth) {
    return ensureOk(first);
  }
  const token = await session.refreshAccessToken();
  if (token === null) {
    session.onSessionLost();
    throw await toApiError(first);
  }
  const second = await send(path, options, token);
  if (second.status === 401) {
    session.onSessionLost();
  }
  return ensureOk(second);
}

async function send(path: string, options: CallOptions, token: string | null): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json', ...options.headers };
  const init: RequestInit = { method: options.method ?? 'GET', credentials: 'include', headers };
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(options.body);
  }
  if (token !== null) {
    headers.Authorization = `Bearer ${token}`;
  }
  try {
    return await fetch(new URL(path, window.location.origin), init);
  } catch {
    throw new ApiError(0, 'network_error', 'The server could not be reached.');
  }
}

async function ensureOk(response: Response): Promise<Response> {
  if (!response.ok) {
    throw await toApiError(response);
  }
  return response;
}

async function toApiError(response: Response): Promise<ApiError> {
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  const retryAfter = parseRetryAfter(response.headers.get('Retry-After'));
  const parsed = errorEnvelopeSchema.safeParse(payload);
  if (parsed.success) {
    const { code, message, fields } = parsed.data.error;
    return new ApiError(response.status, code, message, fields ?? {}, retryAfter);
  }
  return new ApiError(
    response.status,
    'unknown_error',
    `The request failed with status ${response.status}.`,
    {},
    retryAfter,
  );
}

function parseRetryAfter(value: string | null): number | null {
  if (value === null) return null;
  const seconds = Number.parseInt(value, 10);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}
