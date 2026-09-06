import { describe, expect, it } from 'vitest';

import { ApiError, asApiError, describeError, isApiError } from './errors';

describe('ApiError helpers', () => {
  it('exposes field reasons', () => {
    const error = new ApiError(422, 'validation_error', 'Invalid.', { email: 'Enter an email.' });
    expect(error.fieldError('email')).toBe('Enter an email.');
    expect(error.fieldError('other')).toBeUndefined();
    expect(error.name).toBe('ApiError');
    expect(isApiError(error)).toBe(true);
    expect(isApiError(new Error('x'))).toBe(false);
  });

  it('describes API errors with their message', () => {
    expect(describeError(new ApiError(401, 'invalid_credentials', 'Incorrect email.'))).toBe(
      'Incorrect email.',
    );
  });

  it('describes rate limits with and without a retry hint', () => {
    expect(describeError(new ApiError(429, 'rate_limited', 'x', {}, 45))).toBe(
      'Too many attempts. Try again in 45 seconds.',
    );
    expect(describeError(new ApiError(429, 'rate_limited', 'x'))).toBe('Too many attempts.');
  });

  it('hides unknown failures behind a generic message', () => {
    expect(describeError(new Error('stack details'))).toBe(
      'Something went wrong. Please try again.',
    );
    expect(describeError('oops')).toBe('Something went wrong. Please try again.');
  });

  it('normalises any value to an ApiError', () => {
    const original = new ApiError(500, 'server_error', 'Boom.');
    expect(asApiError(original)).toBe(original);
    expect(asApiError(new TypeError('x'))).toMatchObject({ status: 0, code: 'unexpected_error' });
  });
});
