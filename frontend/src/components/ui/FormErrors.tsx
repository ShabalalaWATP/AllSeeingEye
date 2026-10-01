/**
 * The error summary for a rejected form. With field reasons it names each failing field as
 * a link that moves focus to the control and takes focus itself when a new rejection
 * arrives. Without field reasons it shows an already safe string as given, or the safe
 * generic message for any other failure. The generic
 * "The request is invalid." only heads the list when no reason matched a field on the form.
 */
import { useEffect, useId, useRef } from 'react';
import type { MouseEvent } from 'react';

import { describeError } from '@/lib/api/errors';
import type { FieldErrors } from '@/lib/api/fieldErrors';

import { Alert } from './Alert';

const FOCUSABLE = 'input, select, textarea, button, summary, a[href], [tabindex]';
const ENABLED_CONTROL =
  'input:not([disabled]):not([type="hidden"]), select:not([disabled]), ' +
  'textarea:not([disabled]), button:not([disabled]), summary, a[href]';

/** Focuses the element with this id, or the first usable control inside it. */
export function focusFieldTarget(id: string): boolean {
  const element = document.getElementById(id);
  if (element === null) return false;
  const details = element.closest('details');
  if (details !== null) details.open = true;
  const control = element.matches(FOCUSABLE)
    ? element
    : (element.querySelector<HTMLElement>(ENABLED_CONTROL) ?? element);
  if (!control.matches(FOCUSABLE)) control.setAttribute('tabindex', '-1');
  const scroll: unknown = Reflect.get(control, 'scrollIntoView');
  if (typeof scroll === 'function') scroll.call(control, { block: 'center' });
  control.focus();
  return true;
}

export interface FormErrorsProps {
  errors: FieldErrors;
  className?: string | undefined;
}

export function FormErrors({ errors, className = '' }: FormErrorsProps) {
  const { error, entries, matched } = errors;
  const summary = useRef<HTMLDivElement>(null);
  const headingId = useId();
  const listed = entries.length > 0;
  useEffect(() => {
    if (listed) summary.current?.focus();
  }, [error, listed]);

  if (error === null || error === undefined) return null;
  if (!listed) {
    return (
      <Alert tone="error" className={className}>
        {typeof error === 'string' ? error : describeError(error)}
      </Alert>
    );
  }
  const follow = (event: MouseEvent<HTMLAnchorElement>, target: string) => {
    event.preventDefault();
    if (!focusFieldTarget(target)) summary.current?.focus();
  };
  return (
    <div
      ref={summary}
      tabIndex={-1}
      role="alert"
      aria-labelledby={headingId}
      className={`rounded-md border border-critical/40 bg-critical/10 px-3 py-2 text-sm text-text focus-visible:outline-2 focus-visible:outline-critical ${className}`}
    >
      <p id={headingId} className="font-semibold">
        {matched ? 'Check these fields and try again:' : describeError(error)}
      </p>
      <ul className="mt-2 list-disc space-y-1 pl-5">
        {entries.map((entry) => (
          <li key={entry.key}>
            {entry.target === null ? (
              `${entry.label}: ${entry.message}`
            ) : (
              <a
                href={`#${entry.target}`}
                className="underline underline-offset-2"
                onClick={(event) => follow(event, entry.target ?? '')}
              >
                {entry.label}: {entry.message}
              </a>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
