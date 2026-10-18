import { useId, useRef, useState, type RefObject } from 'react';
import { Link } from 'react-router';

import { PageHeader } from '@/components/ui/PageHeader';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextAreaField, TextField } from '@/components/ui/Field';
import { requestAccount } from '@/lib/api/auth';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

const TERMS_REQUIRED = 'Agree to the Terms and Acceptable Use Policy to request an account.';

/** Required agreement. The policies open in a new tab so the typed request is kept. */
function TermsAgreement({
  ref,
  checked,
  error,
  onChange,
}: {
  ref: RefObject<HTMLInputElement | null>;
  checked: boolean;
  error: string | undefined;
  onChange: (checked: boolean) => void;
}) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <p id={`${id}-hint`} className="text-xs text-muted">
        Read the{' '}
        <a className="underline" href="/terms" target="_blank" rel="noopener noreferrer">
          Terms (opens in a new tab)
        </a>{' '}
        and the{' '}
        <a className="underline" href="/acceptable-use" target="_blank" rel="noopener noreferrer">
          Acceptable Use Policy (opens in a new tab)
        </a>
        .
      </p>
      <div className="flex items-start gap-2">
        <input
          ref={ref}
          id={id}
          name="accept_terms"
          type="checkbox"
          className="mt-1 size-4"
          checked={checked}
          aria-required="true"
          aria-invalid={error === undefined ? undefined : true}
          aria-describedby={[`${id}-hint`, error === undefined ? null : `${id}-error`]
            .filter((value) => value !== null)
            .join(' ')}
          onChange={(event) => {
            onChange(event.target.checked);
          }}
        />
        <label htmlFor={id} className="text-sm text-text">
          I agree to the Terms and Acceptable Use Policy
        </label>
      </div>
      {error === undefined ? null : (
        <p id={`${id}-error`} role="alert" className="text-sm text-critical">
          {error}
        </p>
      )}
    </div>
  );
}

export function RequestAccountPage() {
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [reason, setReason] = useState('');
  const [accepted, setAccepted] = useState(false);
  const [termsMissing, setTermsMissing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const termsBox = useRef<HTMLInputElement>(null);
  const { run, busy, error } = useAsyncAction(async () => {
    const trimmedReason = reason.trim();
    setMessage(
      await requestAccount({
        email,
        display_name: displayName,
        ...(trimmedReason === '' ? {} : { reason: trimmedReason }),
        accept_terms: true,
      }),
    );
  });

  if (message !== null) {
    return (
      <div className="flex flex-col gap-4">
        <PageHeader title="Request received" />
        <Alert tone="success">{message}</Alert>
        <Link to="/login" className="text-sm text-muted hover:text-text">
          Back to sign in
        </Link>
      </div>
    );
  }

  const fieldErrors = error?.code === 'validation_error' ? error.fields : {};
  const termsError = termsMissing ? TERMS_REQUIRED : fieldErrors.accept_terms;

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (!accepted) {
          setTermsMissing(true);
          termsBox.current?.focus();
          return;
        }
        void run();
      }}
    >
      <PageHeader title="Request an account" />
      <p className="text-sm text-muted">
        An administrator reviews every request. You will receive an activation link if it is
        approved.
      </p>
      {error === null || error.code === 'validation_error' ? null : (
        <Alert tone="error">{describeError(error)}</Alert>
      )}
      <TextField
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        required
        value={email}
        error={fieldErrors.email}
        onChange={(event) => {
          setEmail(event.target.value);
        }}
      />
      <TextField
        label="Display name"
        name="display_name"
        autoComplete="name"
        required
        maxLength={80}
        value={displayName}
        error={fieldErrors.display_name}
        onChange={(event) => {
          setDisplayName(event.target.value);
        }}
      />
      <TextAreaField
        label="Reason (optional)"
        name="reason"
        maxLength={500}
        value={reason}
        error={fieldErrors.reason}
        onChange={(event) => {
          setReason(event.target.value);
        }}
      />
      <TermsAgreement
        ref={termsBox}
        checked={accepted}
        error={termsError}
        onChange={(checked) => {
          setAccepted(checked);
          if (checked) setTermsMissing(false);
        }}
      />
      <Button type="submit" busy={busy}>
        Send request
      </Button>
      <Link to="/login" className="text-sm text-muted hover:text-text">
        Back to sign in
      </Link>
    </form>
  );
}
