import { describe, expect, it } from 'vitest';

import { csrfHeaders, readCookie } from './csrf';

describe('csrf cookie helpers', () => {
  it('reads a named cookie and decodes it', () => {
    document.cookie = 'other=1; path=/';
    document.cookie = 'ase_csrf=abc%20def; path=/';
    expect(readCookie('ase_csrf')).toBe('abc def');
    expect(readCookie('other')).toBe('1');
    expect(csrfHeaders()).toEqual({ 'X-CSRF-Token': 'abc def' });
  });

  it('returns null and no header when the cookie is absent', () => {
    expect(readCookie('ase_csrf')).toBeNull();
    expect(csrfHeaders()).toEqual({});
  });
});
