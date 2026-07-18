import { describe, expect, it } from 'vitest'
import { PREFS_DEFAULTS, PrefsUpdateSchema, parsePrefs } from '../src/main/core/prefs-schema'

describe('parsePrefs', () => {
  it('returns defaults for undefined input', () => {
    expect(parsePrefs(undefined)).toEqual(PREFS_DEFAULTS)
  })

  it('returns defaults for a completely corrupt blob', () => {
    expect(parsePrefs('garbage')).toEqual(PREFS_DEFAULTS)
    expect(parsePrefs(42)).toEqual(PREFS_DEFAULTS)
  })

  it('repairs a single corrupt field without losing the rest', () => {
    const out = parsePrefs({ x: 'not-a-number', y: 300, mode: 'security' })
    expect(out.x).toBe(PREFS_DEFAULTS.x)
    expect(out.y).toBe(300)
    expect(out.mode).toBe('security')
  })

  it('falls back to general for an unknown mode', () => {
    expect(parsePrefs({ mode: 'aggressive' }).mode).toBe('general')
  })

  it('round-trips a valid preferences object', () => {
    const prefs = {
      x: 12,
      y: 34,
      mode: 'delivery',
      privacyNoticeDismissed: true,
      startPaused: true
    }
    expect(parsePrefs(prefs)).toEqual(prefs)
  })
})

describe('PrefsUpdateSchema', () => {
  it('accepts the renderer-updatable fields', () => {
    expect(
      PrefsUpdateSchema.safeParse({ mode: 'writing', privacyNoticeDismissed: true }).success
    ).toBe(true)
  })

  it('rejects position updates from the renderer', () => {
    expect(PrefsUpdateSchema.safeParse({ x: 10 }).success).toBe(false)
  })

  it('rejects unknown keys', () => {
    expect(PrefsUpdateSchema.safeParse({ apiKey: 'sk-nope' }).success).toBe(false)
  })
})
