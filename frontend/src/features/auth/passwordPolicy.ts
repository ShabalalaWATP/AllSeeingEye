export const PASSWORD_MIN = 12;
export const PASSWORD_MAX = 128;

export const PASSWORD_POLICY_TEXT =
  `Use ${PASSWORD_MIN} to ${PASSWORD_MAX} characters. Very common passwords and your own ` +
  'email address are not accepted. Length matters more than symbols.';

/** Client-side pre-check; the server applies the full policy. */
export function checkPassword(password: string, confirmation: string): string | null {
  if (password.length < PASSWORD_MIN) {
    return `The password must be at least ${PASSWORD_MIN} characters.`;
  }
  if (password.length > PASSWORD_MAX) {
    return `The password must be no longer than ${PASSWORD_MAX} characters.`;
  }
  if (password !== confirmation) {
    return 'The two passwords do not match.';
  }
  return null;
}
