import type { createEyeRenderer } from './evilEyeRenderer';

let pending: Promise<typeof createEyeRenderer> | undefined;

/** Several public eyes can need the same fallback after worker startup fails. */
export function loadEyeRenderer(): Promise<typeof createEyeRenderer> {
  return (pending ??= import('./evilEyeRenderer').then((module) => module.createEyeRenderer));
}
