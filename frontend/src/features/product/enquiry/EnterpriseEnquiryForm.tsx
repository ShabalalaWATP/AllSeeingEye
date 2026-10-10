import { useId } from 'react';
import { Link } from 'react-router';

import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';

import { DEPLOYMENTS, USER_COUNTS, type EnquiryDraft } from './enquiryFields';
import { useEnterpriseEnquiry } from './useEnterpriseEnquiry';

const CONTACT_FIELDS = [
  { name: 'name', label: 'Name', autoComplete: 'name', maxLength: 100, required: true },
  { name: 'email', label: 'Work email', autoComplete: 'email', maxLength: 254, required: true },
  {
    name: 'organisation',
    label: 'Organisation',
    autoComplete: 'organization',
    maxLength: 150,
    required: true,
  },
  {
    name: 'role',
    label: 'Role (optional)',
    autoComplete: 'organization-title',
    maxLength: 100,
    required: false,
  },
] as const;

export function EnterpriseEnquiryForm() {
  const { draft, errors, phase, feedback, feedbackRef, update, submit } = useEnterpriseEnquiry();
  const id = useId();
  const busy = phase === 'submitting';
  const finished = phase === 'success' || phase === 'unavailable';
  return (
    <div className="enterprise-enquiry">
      <h3 className="text-xl font-semibold" id={`${id}-title`}>
        Enquire about self-hosting
      </h3>
      <p className="mt-2 text-sm text-muted">
        Tell us about your organisation. Please do not include passwords or sensitive research.
      </p>
      <div
        ref={feedbackRef}
        tabIndex={-1}
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className={
          feedback === null ? 'sr-only' : 'my-5 rounded border border-control-border p-4 text-sm'
        }
      >
        {feedback?.message}
      </div>
      {finished ? null : (
        <form
          aria-labelledby={`${id}-title`}
          aria-busy={busy}
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <div className="enquiry-fields">
            {CONTACT_FIELDS.map((field) => (
              <TextField
                key={field.name}
                {...field}
                id={`${id}-${field.name}`}
                type={field.name === 'email' ? 'email' : 'text'}
                value={draft[field.name]}
                error={errors[field.name]}
                disabled={busy}
                onChange={(event) => update(field.name, event.target.value)}
              />
            ))}
            <SelectField
              id={`${id}-deployment`}
              name="deployment_interest"
              label="Deployment interest"
              required
              options={DEPLOYMENTS}
              value={draft.deployment_interest}
              error={errors.deployment_interest}
              disabled={busy}
              onChange={(event) =>
                update(
                  'deployment_interest',
                  event.target.value as EnquiryDraft['deployment_interest'],
                )
              }
            />
            <SelectField
              id={`${id}-users`}
              name="expected_users"
              label="Expected users"
              required
              options={USER_COUNTS}
              value={draft.expected_users}
              error={errors.expected_users}
              disabled={busy}
              onChange={(event) =>
                update('expected_users', event.target.value as EnquiryDraft['expected_users'])
              }
            />
          </div>
          <TextAreaField
            id={`${id}-message`}
            name="message"
            label="Message (optional)"
            maxLength={2000}
            rows={5}
            hint={`${draft.message.length.toLocaleString('en-GB')} / 2,000 characters`}
            value={draft.message}
            error={errors.message}
            disabled={busy}
            onChange={(event) => update('message', event.target.value)}
          />
          <div className="sr-only" aria-hidden="true">
            <label htmlFor={`${id}-website`}>Website</label>
            <input
              id={`${id}-website`}
              name="website"
              type="text"
              aria-hidden="true"
              tabIndex={-1}
              autoComplete="off"
              maxLength={200}
              value={draft.website}
              onChange={(event) => update('website', event.target.value)}
            />
          </div>
          <div className="my-5">
            <label className="flex items-start gap-3 text-sm leading-6" htmlFor={`${id}-privacy`}>
              <input
                id={`${id}-privacy`}
                type="checkbox"
                name="privacyRead"
                required
                disabled={busy}
                className="mt-1 size-4 shrink-0 accent-ember"
                checked={draft.privacyRead}
                aria-invalid={errors.privacyRead === undefined ? undefined : true}
                aria-describedby={
                  errors.privacyRead === undefined ? undefined : `${id}-privacy-error`
                }
                onChange={(event) => update('privacyRead', event.target.checked)}
              />
              <span>
                I have read the{' '}
                <Link to="/privacy" target="_blank" rel="noopener noreferrer" className="underline">
                  privacy notice (opens in a new tab)
                </Link>
                .
              </span>
            </label>
            {errors.privacyRead === undefined ? null : (
              <p id={`${id}-privacy-error`} role="alert" className="mt-2 text-sm text-critical">
                {errors.privacyRead}
              </p>
            )}
          </div>
          <Button type="submit" busy={busy} busyLabel="Sending enquiry…" className="min-h-11">
            Send enquiry
          </Button>
        </form>
      )}
    </div>
  );
}
