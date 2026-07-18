import Store from 'electron-store'
import { parsePrefs } from './core/prefs-schema'
import type { Preferences } from '../shared/types'

/**
 * Thin persistence wrapper. Everything read from disk goes through the zod
 * fallback parser so a corrupt preferences file can never crash the app.
 * Never stores screenshots, analysis text, API responses or keys.
 */
export class PrefsStore {
  private store = new Store({ name: 'preferences' })

  get(): Preferences {
    return parsePrefs(this.store.store)
  }

  set(patch: Partial<Preferences>): void {
    const next = { ...this.get(), ...patch }
    this.store.set(next as unknown as Record<string, unknown>)
  }
}
