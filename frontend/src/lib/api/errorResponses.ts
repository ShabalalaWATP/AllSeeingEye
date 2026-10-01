/**
 * Plain-language errors for HTTP responses that carry no valid application envelope, such
 * as a proxy's HTML 502 page or an empty 413. The response body is never read into the
 * message: only the status and the Retry-After header are trusted. The status stays as a
 * secondary reference so support can match it, never as the only explanation.
 */
import { ApiError } from './errors';

const UNAVAILABLE = new Set([502, 503, 504]);

function reference(status: number): string {
  return `Reference: HTTP ${String(status)}.`;
}

/** Builds the ApiError for a failed response whose body was not a valid error envelope. */
export function unexpectedResponseError(status: number, retryAfter: number | null): ApiError {
  if (UNAVAILABLE.has(status)) {
    return new ApiError(
      status,
      'service_unavailable',
      `The service is temporarily unavailable. Please try again later. ${reference(status)}`,
      {},
      retryAfter,
    );
  }
  if (status === 413) {
    return new ApiError(
      status,
      'payload_too_large',
      `The submitted content is too large. Reduce its size and try again. ${reference(status)}`,
    );
  }
  if (status === 429) {
    return new ApiError(status, 'rate_limited', 'Too many attempts.', {}, retryAfter);
  }
  return new ApiError(
    status,
    'unknown_error',
    `The server could not complete the request. ${reference(status)}`,
    {},
    retryAfter,
  );
}

/** Reads Retry-After as delay seconds or an HTTP date; anything else is ignored. */
export function parseRetryAfter(value: string | null): number | null {
  if (value === null) return null;
  const trimmed = value.trim();
  if (/^\d+$/.test(trimmed)) return Number.parseInt(trimmed, 10);
  if (!/[a-z]/i.test(trimmed)) return null;
  const when = Date.parse(trimmed);
  if (!Number.isFinite(when)) return null;
  return Math.max(0, Math.ceil((when - Date.now()) / 1000));
}
