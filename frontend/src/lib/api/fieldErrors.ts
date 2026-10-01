/**
 * Maps the validation reasons in an ApiError (`fields`, keyed by dotted FastAPI `loc` paths
 * such as `scope.country_isos` or `countries.0`) to the fields a form declares, so each
 * reason can sit beside the control that caused it. Paths that match no declared field are
 * kept, with a readable label, so the summary never silently drops a reason. Reasons are
 * plain text and are only ever rendered as text.
 */
import { useId } from 'react';

import { isApiError } from './errors';

/** A label, or a label with the API paths it owns and an element id to focus instead. */
export type FieldSpec = string | { label: string; paths?: readonly string[]; target?: string };

export interface FieldErrorEntry {
  key: string;
  label: string;
  message: string;
  /** Element id the summary moves focus to; null when no field on the form matches. */
  target: string | null;
}

export interface FieldErrors<K extends string = string> {
  /** The failure these reasons came from, for the generic fallback message. */
  error: unknown;
  /** Matched fields in declared order, then unmatched paths in server order. */
  entries: readonly FieldErrorEntry[];
  /** True when at least one reason belongs to a declared field. */
  matched: boolean;
  message(name: K): string | undefined;
}

const MAX_LABEL = 120;
const MAX_MESSAGE = 300;

function clip(value: string, limit: number): string {
  return value.length <= limit ? value : `${value.slice(0, limit - 1)}…`;
}

/** Options for one form's mapping. */
export interface FieldErrorOptions {
  /** Path prefix that wraps this form's request (such as `report`), left out of labels. */
  root?: string;
}

function readableLabel(path: string, root: string | undefined): string {
  const local =
    root !== undefined && path.startsWith(`${root}.`) ? path.slice(root.length + 1) : path;
  if (local === 'body' || local === '') return 'Request';
  const words = local
    .split('.')
    .map((part) => (/^\d+$/.test(part) ? `item ${String(Number(part) + 1)}` : part))
    .join(' ')
    .replace(/_/g, ' ')
    .trim();
  return clip(words.charAt(0).toUpperCase() + words.slice(1), MAX_LABEL);
}

function specPaths(key: string, spec: FieldSpec): readonly string[] {
  return typeof spec === 'string' ? [key] : (spec.paths ?? [key]);
}

function bestField(path: string, fields: Readonly<Record<string, FieldSpec>>): string | null {
  let best: string | null = null;
  let length = -1;
  for (const [key, spec] of Object.entries(fields)) {
    for (const candidate of specPaths(key, spec)) {
      const hit = path === candidate || path.startsWith(`${candidate}.`);
      if (hit && candidate.length > length) {
        best = key;
        length = candidate.length;
      }
    }
  }
  return best;
}

export function mapFieldErrors<K extends string>(
  error: unknown,
  fields: Readonly<Record<K, FieldSpec>>,
  idFor: (name: K) => string,
  options: FieldErrorOptions = {},
): FieldErrors<K> {
  const reasons = isApiError(error) ? Object.entries(error.fields) : [];
  const byField = new Map<string, string>();
  const unmatched: FieldErrorEntry[] = [];
  for (const [path, reason] of reasons) {
    const message = clip(reason, MAX_MESSAGE);
    const key = bestField(path, fields);
    if (key === null) {
      unmatched.push({
        key: path,
        label: readableLabel(path, options.root),
        message,
        target: null,
      });
    } else if (!byField.has(key)) {
      byField.set(key, message);
    }
  }
  const matchedEntries: FieldErrorEntry[] = [];
  for (const key of Object.keys(fields) as K[]) {
    const message = byField.get(key);
    if (message === undefined) continue;
    const spec: FieldSpec = fields[key];
    const label = typeof spec === 'string' ? spec : spec.label;
    const target = typeof spec === 'string' ? idFor(key) : (spec.target ?? idFor(key));
    matchedEntries.push({ key, label, message, target });
  }
  return {
    error,
    entries: [...matchedEntries, ...unmatched],
    matched: matchedEntries.length > 0,
    message: (name) => byField.get(name),
  };
}

export interface FieldErrorState<K extends string> extends FieldErrors<K> {
  /** Stable element id for a field, so the summary can move focus to it. */
  id(name: K): string;
  /** `id` and `error` props for TextField, TextAreaField and SelectField. */
  field(name: K): { id: string; error: string | undefined };
}

/** Field reasons for one form, with stable ids for its controls. */
export function useFieldErrors<K extends string>(
  error: unknown,
  fields: Readonly<Record<K, FieldSpec>>,
  options: FieldErrorOptions = {},
): FieldErrorState<K> {
  const prefix = useId();
  const id = (name: K) => `${prefix}-${name}`;
  const mapped = mapFieldErrors(error, fields, id, options);
  return { ...mapped, id, field: (name) => ({ id: id(name), error: mapped.message(name) }) };
}
