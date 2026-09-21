import type { SubscriptionEdition } from '@/lib/api/subscriptionEditions';

/** Admission can return a saved waiting edition before any report job exists. */
export function subscriptionRunNotice(edition: SubscriptionEdition): string {
  if (edition.workflow === 'blocked') {
    if (edition.safe_reason === 'research_usage_limit') {
      return "The subscription owner's research allowance is used. This edition will retry after the allowance resets or an administrator increases their level. No new report has been queued.";
    }
    if (edition.safe_reason === 'monthly_budget_exhausted') {
      return 'The monthly AI provider budget is used. This edition will retry when that budget is available. No new report has been queued.';
    }
    return 'This edition is blocked. Open edition history to review its status before retrying.';
  }
  const messages: Record<Exclude<SubscriptionEdition['workflow'], 'blocked'>, string> = {
    pending:
      edition.safe_reason === 'capacity_wait'
        ? 'This edition is waiting for queue space. No new report has been queued yet. It will retry automatically; Run now checks the same edition.'
        : 'This edition is waiting to start. No new report has been queued yet. Run now checks the same edition.',
    queued: 'A new report has been queued. Follow its progress in edition history.',
    running: 'This edition is already running. Follow its progress in edition history.',
    retry_wait: 'This edition is waiting to retry. Follow its progress in edition history.',
    paused: 'This edition is paused. Resume it from edition history when you are ready.',
    completed: 'This edition has completed. Open edition history to read its report.',
    failed:
      'This edition failed. Open edition history to review the failure and available actions.',
    cancelled: 'This edition was cancelled. Open edition history to review its status.',
    skipped: 'This edition was skipped. Open edition history to review its status.',
  };
  return messages[edition.workflow];
}

export function retainSubscriptionRequest(edition: SubscriptionEdition): boolean {
  return edition.job_id === null && ['pending', 'blocked'].includes(edition.workflow);
}
