import { describe, expect, it } from 'vitest';

import { sessionIdentity, responseIdentity } from './sessionIdentity';
import { accessTokenFor } from '@/test/accessTokens';
import { sessionActivity } from '@/test/fixtures';

const encode = (claims: unknown) => `header.${btoa(JSON.stringify(claims))}.signature`;

describe('session continuity claims', () => {
  it('reads only account and refresh family from a normal access token', () => {
    expect(sessionIdentity(accessTokenFor('account', 'family'))).toEqual({
      userId: 'account',
      familyId: 'family',
    });
  });

  it.each([
    '',
    'opaque',
    'header.payload',
    '.payload.signature',
    'header..signature',
    'header.payload.',
    'header.@@@@.signature',
    'header.bm90LWpzb24.signature',
    encode(null),
    encode([]),
    encode({ sub: 'account', typ: 'access' }),
    encode({ sub: 'account', sid: '', typ: 'access' }),
    encode({ sub: '', sid: 'family', typ: 'access' }),
    encode({ sub: 123, sid: 'family', typ: 'access' }),
    encode({ sub: 'account', sid: 'family', typ: 'refresh' }),
  ])('rejects malformed or missing identity metadata: %s', (token) => {
    expect(sessionIdentity(token)).toBeNull();
  });

  it('rejects a response whose user differs from its access token', () => {
    expect(() =>
      responseIdentity({
        access_token: accessTokenFor('account'),
        token_type: 'bearer',
        expires_in: 900,
        activity: sessionActivity(),
        user: {
          id: 'other',
          email: 'other@example.com',
          display_name: 'Other',
          role: 'user',
          is_active: true,
          created_at: '',
          last_login_at: null,
        },
      }),
    ).toThrow('unexpected session response');
  });
});
