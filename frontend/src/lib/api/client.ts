/**
 * Fetch wrapper for the ASE API. Sends cookies, injects the bearer token, parses
 * the error envelope into ApiError, validates successful bodies with zod, and on
 * a 401 refreshes the session once. Calls may disable automatic request replay.
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
  /** Reusable binary body for private imports; cannot be combined with a JSON body. */
  rawBody?: Blob;
  signal?: AbortSignal;
  headers?: Record<string, string>;
  /** When true (default) the bearer token is attached and a 401 triggers one refresh and retry. */
  auth?: boolean;
  /** Disable for costly operations: refresh the session, but require an explicit resubmission. */
  retryAfterRefresh?: boolean;
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

/** Performs a request whose successful body is plain text (for example a Markdown export). */
export async function apiText(path: string, options: CallOptions = {}): Promise<string> {
  const response = await execute(path, {
    ...options,
    headers: { Accept: 'text/plain, text/markdown', ...options.headers },
  });
  return response.text();
}

/** Fetches an authenticated binary export through the same session and error handling. */
export async function apiBlob(path: string, options: CallOptions = {}): Promise<Blob> {
  const response = await execute(path, {
    ...options,
    headers: { Accept: 'application/octet-stream', ...options.headers },
  });
  return response.blob();
}

export interface DownloadedFile {
  blob: Blob;
  filename: string | null;
}

/** Fetches a binary or text download together with its safe server-provided file name. */
export async function apiFile(path: string, options: CallOptions = {}): Promise<DownloadedFile> {
  const response = await execute(path, {
    ...options,
    headers: { Accept: 'application/octet-stream', ...options.headers },
  });
  return {
    blob: await response.blob(),
    filename: safeDownloadFilename(response.headers.get('Content-Disposition')),
  };
}

/** Performs a request whose successful response has no body of interest (for example 204). */
export async function apiSend(path: string, options: CallOptions = {}): Promise<void> {
  await execute(path, options);
}

async function execute(path: string, options: CallOptions): Promise<Response> {
  if (options.body !== undefined && options.rawBody !== undefined) {
    throw new ApiError(0, 'invalid_request', 'Choose either a JSON or binary request body.');
  }
  options.signal?.throwIfAborted();
  const auth = options.auth ?? true;
  const first = await send(path, options, auth ? session.getAccessToken() : null);
  if (first.status !== 401 || !auth) {
    return ensureOk(first);
  }
  options.signal?.throwIfAborted();
  const token = await session.refreshAccessToken();
  options.signal?.throwIfAborted();
  if (token === null) {
    session.onSessionLost();
    throw await toApiError(first);
  }
  if (options.retryAfterRefresh === false) {
    throw new ApiError(
      409,
      'request_retry_required',
      'Your session has been refreshed. This request was not repeated automatically. Please submit it again if needed.',
    );
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
  if (options.signal !== undefined) init.signal = options.signal;
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(options.body);
  } else if (options.rawBody !== undefined) {
    headers['Content-Type'] = 'application/octet-stream';
    init.body = options.rawBody;
  }
  if (token !== null) {
    headers.Authorization = `Bearer ${token}`;
  }
  try {
    return await fetch(new URL(path, window.location.origin), init);
  } catch (error) {
    if (options.signal?.aborted) throw options.signal.reason;
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
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

function safeDownloadFilename(disposition: string | null): string | null {
  if (disposition === null) return null;
  const match = /(?:^|;)\s*filename="([^"]+)"(?:;|$)/i.exec(disposition);
  const filename = match?.[1];
  return filename !== undefined && /^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/.test(filename)
    ? filename
    : null;
}

function parseRetryAfter(value: string | null): number | null {
  if (value === null) return null;
  const seconds = Number.parseInt(value, 10);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}
