import { useEffect, useRef, useState } from 'react';

import type { BriefDraft } from '@/lib/api/researchBriefSchema';
import { validateBriefDraft } from '@/lib/researchBriefDraft';

import { briefIssueStep, type BriefStep } from './BriefJourney';

type Input = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;

/** Keep stage navigation and validation focus local to this mounted editor. */
export function useBriefJourney(
  draft: BriefDraft,
  initialStep: BriefStep,
  problem: string | null,
  setProblem: (problem: string) => void,
) {
  const [step, setStep] = useState(initialStep);
  const [validationAttempt, setValidationAttempt] = useState(0);
  const root = useRef<HTMLElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const errorSummary = useRef<HTMLDivElement>(null);
  const invalidField = useRef<Input | null>(null);
  const invalidStep = useRef<BriefStep | null>(null);
  const pendingReview = useRef(false);
  const previousStep = useRef<BriefStep | null>(null);
  useEffect(() => {
    if (pendingReview.current) {
      if (invalidField.current) invalidField.current.focus();
      else heading.current?.focus();
      pendingReview.current = false;
    } else if (previousStep.current !== step && (previousStep.current !== null || step === 'run')) {
      heading.current?.focus();
    }
    previousStep.current = step;
  }, [step]);
  useEffect(() => {
    if (problem) errorSummary.current?.focus();
  }, [problem, validationAttempt]);

  const validate = () => {
    const issue = validateBriefDraft(draft);
    const invalid = root.current?.querySelector<Input>(
      '[data-brief-fields] input:invalid, [data-brief-fields] select:invalid, [data-brief-fields] textarea:invalid',
    );
    if (!issue && !invalid) return true;
    const target = invalid?.closest<HTMLElement>('[data-brief-stage]')?.dataset.briefStage;
    const destination = issue
      ? briefIssueStep(issue)
      : ((target as BriefStep | undefined) ?? 'brief');
    setStep(destination);
    invalidStep.current = destination;
    invalidField.current = target === destination ? (invalid ?? null) : null;
    root.current
      ?.querySelectorAll<HTMLDetailsElement>(`#brief-stage-${destination} details`)
      .forEach((details) => {
        details.open = true;
      });
    const label = invalid?.labels?.[0]?.textContent ?? 'This field';
    const advice = invalid?.validity.rangeOverflow
      ? `use a maximum of ${invalid.getAttribute('max')}.`
      : invalid?.validity.rangeUnderflow
        ? `use at least ${invalid.getAttribute('min')}.`
        : 'review the required value.';
    setProblem(issue ?? `${label}: ${advice}`);
    setValidationAttempt((attempt) => attempt + 1);
    return false;
  };
  const reviewField = () => {
    if (invalidStep.current && step !== invalidStep.current) {
      pendingReview.current = true;
      setStep(invalidStep.current);
    } else if (invalidField.current) invalidField.current.focus();
    else heading.current?.focus();
  };
  return { step, setStep, root, heading, errorSummary, validate, reviewField };
}
