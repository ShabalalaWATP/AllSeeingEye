import { describe, expect, it } from 'vitest';

import { checkPassword } from './passwordPolicy';
import { redirectTarget } from './redirect';

describe('redirectTarget', () => {
  it('honours same-origin absolute paths only', () => {
    expect(redirectTarget({ from: '/' }, '/admin')).toBe('/');
    expect(redirectTarget(undefined, '/admin')).toBe('/admin');
    expect(redirectTarget({ from: '/admin/users?tab=1' })).toBe('/admin/users?tab=1');
    expect(redirectTarget({ from: '//evil.example.com' })).toBe('/');
    expect(redirectTarget({ from: 'https://evil.example.com' })).toBe('/');
    expect(redirectTarget({ from: 42 })).toBe('/');
    expect(redirectTarget(null)).toBe('/');
    expect(redirectTarget(undefined)).toBe('/');
    expect(redirectTarget({})).toBe('/');
  });
});

describe('checkPassword', () => {
  it('applies the length and confirmation rules', () => {
    expect(checkPassword('short', 'short')).toMatch(/at least 12/);
    expect(checkPassword('x'.repeat(129), 'x'.repeat(129))).toMatch(/no longer than 128/);
    expect(checkPassword('a-valid-passphrase', 'different-passphrase')).toBe(
      'The two passwords do not match.',
    );
    expect(checkPassword('a-valid-passphrase', 'a-valid-passphrase')).toBeNull();
  });
});
