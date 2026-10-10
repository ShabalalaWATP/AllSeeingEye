/**
 * Fetch wrapper for the ASE API. Sends cookies, injects the bearer token, parses
 * the error envelope into ApiError, validates successful bodies with zod, and on
 * a 401 refreshes the session once. Calls may disable automatic request replay.
 *
 * The client never imports the auth store (lib must not depend on stores); the
 * store binds itself through `bindSession`.
 */
import { safeParse, type $ZodType as ZodType } from 'zod/v4/core';

import { CSRF_COOKIE, readCookie } from '@/lib/csrf';
import { parseIdleMinutes } from '@/lib/idleMinutes';

import { ApiError, sessionChangedError } from './errors';
import { parseRetryAfter, unexpectedResponseError } from './errorResponses';
import { errorEnvelopeSchema } from './errorEnvelope';

export interface SessionBridge {
  getAccessToken(): string | null;
  /** A login generation stays stable when its access token is refreshed. */
  getSessionGeneration(): number;
  /**
   * Refreshes the session and resolves to the new access token, or null on failure.
   * The refresher decides whether a failure ends the session; a transient one must not.
   */
  refreshAccessToken(): Promise<string | null>;
  onSessionLost(): void;
  /** Explicit idle expiry must never trigger a token refresh. */
  onSessionIdle?(minutes?: number): void;
}

const noSession: SessionBridge = {
  getAccessToken: () => null,
  getSessionGeneration: () => 0,
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
  return execute(path, options, (response) => readJson(response, options.schema));
}

/** A conditional action may return a validated JSON result or204 without a body. */
export function apiOptional<T>(
  path: string,
  options: CallOptions & { schema: ZodType<T> },
): Promise<T | null> {
  return execute(path, options, (response) =>
    response.status === 204 ? Promise.resolve(null) : readJson(response, options.schema),
  );
}

async function readJson<T>(response: Response, schema: ZodType<T>): Promise<T> {
  const data: unknown = await response.json();
  const parsed = safeParse(schema, data);
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
  return execute(
    path,
    {
      ...options,
      headers: { Accept: 'text/plain, text/markdown', ...options.headers },
    },
    (response) => response.text(),
  );
}

/** Fetches an authenticated binary export through the same session and error handling. */
export async function apiBlob(path: string, options: CallOptions = {}): Promise<Blob> {
  return execute(
    path,
    {
      ...options,
      headers: { Accept: 'application/octet-stream', ...options.headers },
    },
    (response) => response.blob(),
  );
}

export interface DownloadedFile {
  blob: Blob;
  filename: string | null;
}

/** Fetches a binary or text download together with its safe server-provided file name. */
export async function apiFile(path: string, options: CallOptions = {}): Promise<DownloadedFile> {
  return execute(
    path,
    {
      ...options,
      headers: { Accept: 'application/octet-stream', ...options.headers },
    },
    async (response) => ({
      blob: await response.blob(),
      filename: safeDownloadFilename(response.headers.get('Content-Disposition')),
    }),
  );
}

/** Performs a request whose successful response has no body of interest (for example 204). */
export async function apiSend(path: string, options: CallOptions = {}): Promise<void> {
  await execute(path, options, () => Promise.resolve());
}

async function execute<T>(
  path: string,
  options: CallOptions,
  read: (response: Response) => Promise<T>,
): Promise<T> {
  const bridge = session;
  const generation = bridge.getSessionGeneration();
  const assertCurrent = () => {
    options.signal?.throwIfAborted();
    if (
      (options.auth ?? true) &&
      (session !== bridge || bridge.getSessionGeneration() !== generation)
    ) {
      throw sessionChangedError();
    }
  };
  const response = await executeResponse(path, options, bridge, assertCurrent);
  const result = await read(response);
  // Response bodies can arrive after their headers, including streamed downloads.
  assertCurrent();
  return result;
}

async function executeResponse(
  path: string,
  options: CallOptions,
  bridge: SessionBridge,
  assertCurrent: () => void,
): Promise<Response> {
  if (options.body !== undefined && options.rawBody !== undefined) {
    throw new ApiError(0, 'invalid_request', 'Choose either a JSON or binary request body.');
  }
  options.signal?.throwIfAborted();
  const auth = options.auth ?? true;
  const first = await send(path, options, auth ? bridge.getAccessToken() : null);
  assertCurrent();
  if (first.status !== 401 || !auth) {
    return ensureOk(first);
  }
  const firstError = await toApiError(first);
  assertCurrent();
  if (firstError.code === 'session_idle_expired') {
    bridge.onSessionIdle?.(parseIdleMinutes(firstError.fields.idle_minutes));
    throw firstError;
  }
  options.signal?.throwIfAborted();
  const token = await bridge.refreshAccessToken();
  // A definite rejection can clear its own session and still retain its 401 error.
  if (token !== null) assertCurrent();
  options.signal?.throwIfAborted();
  if (token === null) {
    throw firstError;
  }
  if (options.retryAfterRefresh === false) {
    throw new ApiError(
      409,
      'request_retry_required',
      'Your session has been refreshed. This request was not repeated automatically. Please submit it again if needed.',
    );
  }
  const retryCookie = readCookie(CSRF_COOKIE);
  const second = await send(path, options, token);
  assertCurrent();
  // Another tab can replace shared cookies and push without changing this tab's generation.
  if (second.status === 401) {
    const error = await toApiError(second);
    assertCurrent();
    if (error.code === 'session_idle_expired')
      bridge.onSessionIdle?.(parseIdleMinutes(error.fields.idle_minutes));
    else if (readCookie(CSRF_COOKIE) === retryCookie) bridge.onSessionLost();
    throw error;
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
    const { code, message, fields, request_id: requestId } = parsed.data.error;
    return new ApiError(
      response.status,
      code,
      message,
      fields ?? {},
      retryAfter,
      requestId ?? null,
    );
  }
  return unexpectedResponseError(response.status, retryAfter);
}

function safeDownloadFilename(disposition: string | null): string | null {
  if (disposition === null) return null;
  const match = /(?:^|;)\s*filename="([^"]+)"(?:;|$)/i.exec(disposition);
  const filename = match?.[1];
  return filename !== undefined && /^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/.test(filename)
    ? filename
    : null;
}
