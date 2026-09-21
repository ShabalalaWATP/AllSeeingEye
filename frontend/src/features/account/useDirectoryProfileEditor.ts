import { useEffect, useState } from 'react';
import { asApiError, describeError } from '@/lib/api/errors';
import {
  getDirectoryProfile,
  updateDirectoryProfile,
  type DirectoryProfile,
} from '@/lib/api/directoryProfile';
import {
  directoryChanges,
  directoryDraft,
  reapplyDirectoryDraft,
  type DirectoryDraft,
} from './directoryProfileDraft';

export function useDirectoryProfileEditor() {
  const [profile, setProfile] = useState<DirectoryProfile | null>(null);
  const [draft, setDraft] = useState<DirectoryDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [latest, setLatest] = useState<DirectoryProfile | null>(null);
  const [needsReload, setNeedsReload] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const value = await getDirectoryProfile();
      setProfile(value);
      setDraft(directoryDraft(value));
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, []);

  const dirty =
    draft !== null &&
    profile !== null &&
    JSON.stringify(draft) !== JSON.stringify(directoryDraft(profile));
  const edit = <K extends keyof DirectoryDraft>(key: K, value: DirectoryDraft[K]) => {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
    setSaved(false);
    setError(null);
  };

  async function reloadLatest() {
    setBusy(true);
    try {
      const value = await getDirectoryProfile();
      setLatest(value.revision !== profile?.revision ? value : null);
      setNeedsReload(false);
    } catch (caught) {
      setNeedsReload(true);
      setError(
        `Could not load the latest profile. Your edits are kept. ${describeError(asApiError(caught))}`,
      );
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (busy || !dirty || latest || needsReload) return;
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updateDirectoryProfile(directoryChanges(draft, profile.revision));
      setProfile(updated);
      setDraft(directoryDraft(updated));
      setSaved(true);
    } catch (caught) {
      const failure = asApiError(caught);
      setError(describeError(failure));
      if (failure.status === 409) await reloadLatest();
    } finally {
      setBusy(false);
    }
  }

  function resolveConflict(keepEdits: boolean) {
    if (!latest || !draft || !profile) return;
    setDraft(keepEdits ? reapplyDirectoryDraft(profile, draft, latest) : directoryDraft(latest));
    setProfile(latest);
    setLatest(null);
    setError(null);
    setSaved(false);
  }

  function reset() {
    if (profile) setDraft(directoryDraft(profile));
    setError(null);
    setSaved(false);
  }

  // Avatar writes advance the revision without discarding unsaved text.
  function avatarChanged(updated: DirectoryProfile) {
    const sync = {
      avatar_url: updated.avatar_url,
      revision: updated.revision,
      updated_at: updated.updated_at,
    };
    setProfile((current) => (current ? { ...current, ...sync } : current));
    setDraft((current) => (current ? { ...current, ...sync } : current));
    setSaved(false);
  }

  return {
    profile,
    draft,
    loading,
    busy,
    error,
    saved,
    latest,
    needsReload,
    dirty,
    load,
    edit,
    submit,
    reset,
    avatarChanged,
    reloadLatest,
    resolveConflict,
  };
}
