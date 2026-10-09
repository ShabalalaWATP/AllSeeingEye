import { useEffect, useRef, useState } from 'react';

import { submitEnterpriseEnquiry } from '@/lib/api/enterpriseEnquiries';
import { isApiError } from '@/lib/api/errors';

import {
  EMPTY_ENQUIRY,
  FIELD_MESSAGES,
  validateEnquiry,
  type EnquiryDraft,
  type EnquiryErrors,
} from './enquiryFields';

export const ENQUIRY_CONFIRMATION = 'Thank you. Your enquiry has been received.';

/** Drafts exist only in this mounted form; no account, storage or analytics calls. */
export function useEnterpriseEnquiry() {
  const [draft, setDraft] = useState<EnquiryDraft>({ ...EMPTY_ENQUIRY });
  const [errors, setErrors] = useState<EnquiryErrors>({});
  const [phase, setPhase] = useState<'editing' | 'submitting' | 'success' | 'unavailable'>(
    'editing',
  );
  const [feedback, setFeedback] = useState<{ message: string } | null>(null);
  const feedbackRef = useRef<HTMLDivElement>(null);
  const request = useRef<AbortController | null>(null);

  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (feedback !== null) feedbackRef.current?.focus();
  }, [feedback]);

  function update<K extends keyof EnquiryDraft>(field: K, value: EnquiryDraft[K]): void {
    setDraft((previous) => ({ ...previous, [field]: value }));
    setErrors((previous) => {
      const { [field]: _previousError, ...remaining } = previous;
      return remaining;
    });
  }

  async function submit(): Promise<void> {
    if (request.current !== null || phase === 'success' || phase === 'unavailable') return;
    const validated = validateEnquiry(draft);
    setErrors(validated.errors);
    if (validated.input === null) {
      setFeedback({ message: 'Please check the marked fields before sending your enquiry.' });
      return;
    }
    const controller = new AbortController();
    request.current = controller;
    setPhase('submitting');
    setFeedback(null);
    try {
      await submitEnterpriseEnquiry(validated.input, controller.signal);
      if (controller.signal.aborted) return;
      setDraft({ ...EMPTY_ENQUIRY });
      setPhase('success');
      setFeedback({ message: ENQUIRY_CONFIRMATION });
    } catch (error: unknown) {
      if (controller.signal.aborted) return;
      setPhase('editing');
      if (isApiError(error) && error.status === 429) {
        setFeedback({ message: 'Enquiries are temporarily limited. Please try again later.' });
      } else if (isApiError(error) && error.status === 404) {
        setPhase('unavailable');
        setFeedback({ message: 'This installation is not accepting enquiries at the moment.' });
      } else if (isApiError(error) && error.status === 422) {
        const fields: EnquiryErrors = {};
        for (const key of Object.keys(FIELD_MESSAGES) as (keyof typeof FIELD_MESSAGES)[]) {
          if (Object.hasOwn(error.fields, key)) fields[key] = FIELD_MESSAGES[key];
        }
        setErrors(fields);
        setFeedback({ message: 'Please check your enquiry details and try again.' });
      } else {
        setFeedback({
          message: 'We could not confirm receipt of your enquiry. Please try again later.',
        });
      }
    } finally {
      request.current = null;
    }
  }

  return { draft, errors, phase, feedback, feedbackRef, update, submit };
}
