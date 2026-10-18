import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import type { TermsStatus } from '@/lib/api/terms';
import { useAuthStore } from '@/stores/auth';

import { useTermsAcceptance } from './useTermsAcceptance';

const versionDate = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
});

function formatVersion(version: string): string {
  const date = new Date(`${version}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? version : versionDate.format(date);
}

/**
 * Blocks the signed-in shells until the account accepts the current Terms. The native modal
 * keeps focus inside and the page inert; Escape and other close requests do nothing, so the
 * only ways out are accepting or signing out. Policies open in a new tab, keeping this state.
 */
export function TermsAcceptanceDialog() {
  const { terms, ...acceptance } = useTermsAcceptance();
  return terms === null ? null : <OpenTermsDialog terms={terms} {...acceptance} />;
}

function OpenTermsDialog({
  terms,
  accept,
  busy,
  error,
}: { terms: TermsStatus } & Omit<ReturnType<typeof useTermsAcceptance>, 'terms'>) {
  const dialog = useRef<HTMLDialogElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const title = useId();
  const description = useId();
  const changed = terms.accepted_version !== null;

  useEffect(() => {
    const opener = document.activeElement;
    const element = dialog.current;
    // Page shortcuts must not see keys meant for this dialog, including Escape.
    const stopKeys = (event: KeyboardEvent) => event.stopPropagation();
    element?.addEventListener('keydown', stopKeys);
    element?.showModal();
    heading.current?.focus();
    return () => {
      element?.close();
      element?.removeEventListener('keydown', stopKeys);
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);

  return createPortal(
    <dialog
      ref={dialog}
      aria-modal="true"
      aria-labelledby={title}
      aria-describedby={description}
      className="m-auto w-[min(34rem,calc(100vw-2rem))] rounded-card border border-line bg-surface p-5 text-text shadow-card backdrop:bg-black/65"
      onCancel={(event) => event.preventDefault()}
    >
      <h2
        id={title}
        ref={heading}
        tabIndex={-1}
        className="text-lg font-semibold focus:outline-none"
      >
        {changed ? 'The Terms have changed' : 'Accept the Terms to continue'}
      </h2>
      <div id={description} className="mt-3 space-y-2 text-sm leading-6 text-muted">
        <p>
          To keep using The All Seeing Eye, review and accept the Terms and Acceptable Use Policy,
          version of {formatVersion(terms.current_version)}.
        </p>
        <p>Both open in a new tab, so you can return here when you have read them.</p>
      </div>
      <ul className="mt-3 space-y-1 text-sm">
        <li>
          <a
            className="text-ember underline"
            href="/terms"
            target="_blank"
            rel="noopener noreferrer"
          >
            Terms (opens in a new tab)
          </a>
        </li>
        <li>
          <a
            className="text-ember underline"
            href="/acceptable-use"
            target="_blank"
            rel="noopener noreferrer"
          >
            Acceptable Use Policy (opens in a new tab)
          </a>
        </li>
      </ul>
      {error === null ? null : (
        <div className="mt-3">
          <Alert tone="error">{describeError(error)}</Alert>
        </div>
      )}
      <div className="mt-5 flex flex-wrap justify-end gap-2">
        <Button
          variant="secondary"
          onClick={() => {
            void useAuthStore.getState().logout();
          }}
        >
          Sign out
        </Button>
        <Button
          busy={busy}
          busyLabel="Recording your acceptance…"
          onClick={() => {
            void accept(terms.current_version);
          }}
        >
          Accept and continue
        </Button>
      </div>
    </dialog>,
    document.body,
  );
}
