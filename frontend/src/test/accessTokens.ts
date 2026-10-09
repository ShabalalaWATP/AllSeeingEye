/** Synthetic unsigned tokens for continuity tests. They are never server credentials. */
export function accessTokenFor(
  userId: string,
  familyId = `test-family-${userId}`,
  revision = 'initial',
): string {
  const encode = (value: unknown) =>
    btoa(JSON.stringify(value)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
  return `${encode({ alg: 'none' })}.${encode({ sub: userId, sid: familyId, typ: 'access', jti: revision })}.test`;
}
