import type { ScheduleIssue } from './scheduleDraft';

function controlFor(root: HTMLFormElement, field: string): HTMLElement | null {
  if (field === 'Countries')
    return root.querySelector<HTMLElement>('fieldset[aria-describedby] details summary');
  if (field === 'Area disclosure')
    return (
      Array.from(root.querySelectorAll('label'))
        .find((label) => label.textContent.includes('Allow source providers to receive this area'))
        ?.querySelector<HTMLElement>('input') ?? null
    );
  return Array.from(root.querySelectorAll('label')).find(
    (label) => label.textContent.trim() === field,
  )?.control as HTMLElement | null;
}

export function focusScheduleIssue(root: HTMLFormElement | null, issue: ScheduleIssue) {
  if (!root) return;
  if (issue.advanced) {
    const details = root.querySelector<HTMLDetailsElement>('#subscription-advanced');
    if (details) details.open = true;
  }
  const target = controlFor(root, issue.field);
  const scroll: unknown = target && Reflect.get(target, 'scrollIntoView');
  if (typeof scroll === 'function') scroll.call(target, { block: 'center' });
  target?.focus();
}

export function scheduleIssueTarget(issue: ScheduleIssue) {
  if (issue.advanced) return 'subscription-advanced';
  if (issue.field === 'Subscription name') return 'subscription-name';
  if (issue.field === 'Question') return 'subscription-question';
  if (issue.field === 'Nation' || issue.field === 'Countries') return 'subscription-countries';
  if (issue.field === 'Regions') return 'subscription-regions';
  if (issue.field === 'Themes') return 'subscription-themes';
  if (issue.field === 'Area disclosure') return 'subscription-coverage';
  return 'subscription-timing';
}
