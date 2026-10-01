/**
 * ApiError carries the backend error envelope `{error: {code, message, fields}}`
 * plus the HTTP status, so pages can branch on `code` and show field reasons.
 */
export class ApiError extends Error {
  readonly requestId: string | null;
  readonly status: number;
  readonly code: string;
  readonly fields: Readonly<Record<string, string>>;
  readonly retryAfterSeconds: number | null;

  constructor(
    status: number,
    code: string,
    message: string,
    fields: Record<string, string> = {},
    retryAfterSeconds: number | null = null,
    requestId: string | null = null,
  ) {
    super(message);
    this.name = 'ApiError';
    this.requestId = requestId;
    this.status = status;
    this.code = code;
    this.fields = fields;
    this.retryAfterSeconds = retryAfterSeconds;
  }

  fieldError(name: string): string | undefined {
    return this.fields[name];
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

/** Normalises any thrown value to an ApiError so pages can branch on `code`. */
export function asApiError(value: unknown): ApiError {
  if (isApiError(value)) return value;
  return new ApiError(0, 'unexpected_error', 'Something went wrong. Please try again.');
}

/** A safe, human readable message for any thrown value. Never echoes raw payloads. */
export function describeError(value: unknown): string {
  if (isApiError(value)) {
    if (value.status === 429 && !['research_usage_limit', 'ai_usage_limit'].includes(value.code)) {
      const wait =
        value.retryAfterSeconds === null
          ? 'Wait a few minutes before trying again.'
          : describeRetryWait(value.retryAfterSeconds);
      return `Too many attempts. ${wait}`;
    }
    return value.message;
  }
  return 'Something went wrong. Please try again.';
}

/** "Try again in 20 seconds." or "Try again in about 5 minutes." for a known wait. */
function describeRetryWait(seconds: number): string {
  if (seconds <= 90) return `Try again in ${String(seconds)} seconds.`;
  const minutes = Math.ceil(seconds / 60);
  return minutes < 120
    ? `Try again in about ${String(minutes)} minutes.`
    : `Try again in about ${String(Math.ceil(minutes / 60))} hours.`;
}
