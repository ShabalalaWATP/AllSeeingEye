/**
 * ApiError carries the backend error envelope `{error: {code, message, fields}}`
 * plus the HTTP status, so pages can branch on `code` and show field reasons.
 */
export class ApiError extends Error {
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
  ) {
    super(message);
    this.name = 'ApiError';
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
        value.retryAfterSeconds === null ? '' : ` Try again in ${value.retryAfterSeconds} seconds.`;
      return `Too many attempts.${wait}`;
    }
    return value.message;
  }
  return 'Something went wrong. Please try again.';
}
