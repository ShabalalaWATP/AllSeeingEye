/**
 * Unsent research, subscription and alert rule drafts, kept so a click on the bell, the rail
 * or a notification does not discard them.
 *
 * Privacy: drafts live only in this page's memory, never in localStorage, sessionStorage,
 * IndexedDB or a URL. They are keyed by the signed-in account and the current access
 * revision, and every draft is discarded on sign-out, account change, role or activity change
 * and any workspace access change. A reload or a closed tab therefore loses them; forms that
 * hold work which cannot be restored ask before leaving instead (see useLeaveConfirmation).
 * Callers store only what the person typed or chose in that form, never secrets, uploaded
 * files or another account's data.
 */
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type SetStateAction,
} from 'react';

import { useAuthStore, type AuthState } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from './workspaceAccess';

type Fields = Map<string, unknown>;
const drafts = new Map<string, Fields>();
const listeners = new Set<() => void>();
const changed = () => {
  for (const listener of listeners) listener();
};
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function identity(state: AuthState): string | null {
  const user = state.user;
  if (state.status !== 'authenticated' || !user?.is_active) return null;
  return `${user.id}:${user.role}`;
}

function key(form: string): string | null {
  const account = identity(useAuthStore.getState());
  return account === null ? null : `${account}:${workspaceRevision()}|${form}`;
}

export function readDraft(form: string): ReadonlyMap<string, unknown> | undefined {
  const name = key(form);
  return name === null ? undefined : drafts.get(name);
}

export const hasDraft = (form: string) => (readDraft(form)?.size ?? 0) > 0;

function writeField(form: string, field: string, value: unknown) {
  const name = key(form);
  if (name === null) return;
  const fields = drafts.get(name) ?? new Map<string, unknown>();
  fields.set(field, value);
  drafts.set(name, fields);
  changed();
}

export function clearDraft(form: string) {
  const name = key(form);
  if (name !== null && drafts.delete(name)) changed();
}

export function clearAllDrafts() {
  if (drafts.size === 0) return;
  drafts.clear();
  changed();
}

/** Whether a form currently holds unsent work, for leave and reload warnings. */
export function useHasDraft(form: string | null): boolean {
  return useSyncExternalStore(subscribe, () => form !== null && hasDraft(form));
}

/** Draft names. A link's own context (its query string) gets a separate draft. */
export const draftForms = {
  research: (search: string) => `research${search}`,
  subscription: (question: string, country: string) => `subscription:new:${country}:${question}`,
  alertRule: (areaDraft: number | undefined) => `alert-rule:${areaDraft ?? 'new'}`,
};

/** For tests and diagnostics: how many forms currently hold a draft. */
export const draftCount = () => drafts.size;

subscribeWorkspaceAccess(clearAllDrafts);
useAuthStore.subscribe((state, previous) => {
  if (identity(state) !== identity(previous)) clearAllDrafts();
});

const unchanged = <T>(value: T) => value;

/**
 * `useState` whose edits are also kept in the form's in-memory draft. A null form keeps
 * nothing, for example while editing an existing saved record. Untouched fields are never
 * stored, so a form with no edits has no draft.
 */
export function useDraftState<T>(
  form: string | null,
  field: string,
  initial: T | (() => T),
  /** What may be kept, for example a value without an attached private file. */
  keep: (value: T) => T = unchanged,
): [T, (next: SetStateAction<T>) => void] {
  const [value, setValue] = useState<T>(() => {
    const saved = form === null ? undefined : readDraft(form);
    if (saved?.has(field)) return saved.get(field) as T;
    return initial instanceof Function ? initial() : initial;
  });
  const edited = useRef(false);
  useEffect(() => {
    if (edited.current && form !== null) writeField(form, field, keep(value));
  }, [form, field, value, keep]);
  const update = useCallback((next: SetStateAction<T>) => {
    edited.current = true;
    setValue(next);
  }, []);
  return [value, update];
}
