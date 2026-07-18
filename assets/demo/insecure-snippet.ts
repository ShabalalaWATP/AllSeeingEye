// Demo asset: a deliberately insecure, non-functional snippet for showing
// AllSeeingEye's Security mode. Every credential below is fake. Do not reuse
// any of this code anywhere.

const API_SECRET = 'live_secret_EXAMPLE_DO_NOT_SHIP_0000' // hardcoded secret

export async function getUser(db: { query: (sql: string) => Promise<unknown> }, userId: string) {
  // SQL assembled by string concatenation from request input
  return db.query("SELECT * FROM users WHERE id = '" + userId + "'")
}

export function verifySession(token: string, jwt: { verify: Function }) {
  // Accepts unsigned tokens
  return jwt.verify(token, API_SECRET, { algorithms: ['none', 'HS256'] })
}

export function buildProfile(claims: { name?: string; admin?: boolean }) {
  // Privileged by default when the claim is missing
  return { name: claims.name ?? 'anonymous', isAdmin: claims.admin ?? true }
}

// Payments posted over plain HTTP
export const PAYMENTS_ENDPOINT = 'http://payments.internal.example.com/charge'
