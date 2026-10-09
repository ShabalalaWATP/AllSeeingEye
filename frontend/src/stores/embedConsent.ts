import { create } from 'zustand';

import { embedProviderIds, type EmbedProvider } from '@/lib/embedProviders';
import { readStored, safeLocalStorage, writeStored } from '@/lib/safeStorage';
import { useAuthStore } from './auth';

/** Optional browser preference, written only after the separate persistent opt-in. */
export const EMBED_CONSENT_KEY = 'ase.embed-consent.v1';
type Choice = 'session' | 'browser' | null;
type Choices = Record<EmbedProvider, Choice>;
const emptyChoices: Choices = { tradingview: null, youtube: null, ipcamlive: null };
const emptyRevisions = { tradingview: 0, youtube: 0, ipcamlive: 0 };
// A failed removal must not be undone by re-reading the stale saved grant later.
const pendingWithdrawals = new Set<EmbedProvider>();
const withdrawalWarning = () =>
  pendingWithdrawals.size
    ? 'Media is blocked here, but the browser could not clear the saved choice. Clear this site’s browser data before reopening it.'
    : null;

function savedProviders(): EmbedProvider[] {
  try {
    const raw = readStored(EMBED_CONSENT_KEY);
    if (!raw) return [];
    const value: unknown = JSON.parse(raw);
    if (!value || typeof value !== 'object' || !('version' in value) || value.version !== 1)
      return [];
    if (!('providers' in value) || !Array.isArray(value.providers)) return [];
    if (!value.providers.every((item: unknown) => embedProviderIds.includes(item as EmbedProvider)))
      return [];
    return [...new Set(value.providers)] as EmbedProvider[];
  } catch {
    return [];
  }
}

function savedChoices(): Choices {
  const choices = { ...emptyChoices };
  for (const provider of savedProviders())
    if (!pendingWithdrawals.has(provider)) choices[provider] = 'browser';
  return choices;
}

function saveProviders(providers: EmbedProvider[]): boolean {
  const value = providers.length ? JSON.stringify({ version: 1, providers }) : null;
  if (value === null) safeLocalStorage.removeItem(EMBED_CONSENT_KEY);
  else writeStored(EMBED_CONSENT_KEY, value);
  // Guarded storage may fail (private mode, quota, policy). Do not claim success blindly.
  try {
    return window.localStorage.getItem(EMBED_CONSENT_KEY) === value;
  } catch {
    return false;
  }
}

interface EmbedConsentState {
  choices: Choices;
  revisions: Record<EmbedProvider, number>;
  error: string | null;
  remember: (provider: EmbedProvider, persistent: boolean) => void;
  forget: (provider: EmbedProvider) => void;
  resetSession: () => void;
  syncBrowserChoices: () => void;
}

export const useEmbedConsentStore = create<EmbedConsentState>()((set, get) => ({
  choices: savedChoices(),
  revisions: { ...emptyRevisions },
  error: null,
  remember: (provider, persistent) => {
    const saved = persistent && saveProviders([...new Set([...savedProviders(), provider])]);
    if (saved) pendingWithdrawals.delete(provider);
    set({
      choices: { ...get().choices, [provider]: saved ? 'browser' : 'session' },
      error:
        persistent && !saved
          ? `The browser could not save this choice. It is remembered for this session only. ${withdrawalWarning() ?? ''}`.trim()
          : withdrawalWarning(),
    });
  },
  forget: (provider) => {
    const saved = saveProviders(savedProviders().filter((item) => item !== provider));
    if (saved) pendingWithdrawals.delete(provider);
    else pendingWithdrawals.add(provider);
    set({
      choices: { ...get().choices, [provider]: null },
      revisions: { ...get().revisions, [provider]: get().revisions[provider] + 1 },
      error: withdrawalWarning(),
    });
  },
  resetSession: () => {
    const revisions = { ...get().revisions };
    for (const provider of embedProviderIds) revisions[provider] += 1;
    set({ choices: savedChoices(), revisions, error: withdrawalWarning() });
  },
  syncBrowserChoices: () => {
    const { choices, revisions } = get();
    const next = savedChoices();
    const updated = { ...revisions };
    for (const provider of embedProviderIds) {
      if (choices[provider] === 'session' && next[provider] === null) next[provider] = 'session';
      if (choices[provider] === 'browser' && next[provider] === null) updated[provider] += 1;
    }
    set({ choices: next, revisions: updated });
  },
}));

// Session choices belong to the current account's visit, not to rotating access tokens.
useAuthStore.subscribe((state, previous) => {
  if (
    state.status !== previous.status ||
    state.user?.id !== previous.user?.id ||
    state.user?.is_active !== previous.user?.is_active
  )
    useEmbedConsentStore.getState().resetSession();
});

if (typeof window !== 'undefined')
  window.addEventListener('storage', (event) => {
    if (event.key === EMBED_CONSENT_KEY || event.key === null)
      useEmbedConsentStore.getState().syncBrowserChoices();
  });
