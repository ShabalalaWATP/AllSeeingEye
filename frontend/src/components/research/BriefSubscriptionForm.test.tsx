import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import type { ResearchBrief } from '@/lib/api/researchBriefSchema';
import { newBriefDraft } from '@/lib/researchBriefDraft';
import { BriefSubscriptionForm } from './BriefSubscriptionForm';

const brief = {
  ...newBriefDraft(),
  identity: { title: 'Port watch', revision: 1 },
} as unknown as ResearchBrief;

it('rejects an empty time and allows the operator to correct it to midnight', () => {
  const onCreate = vi.fn();
  render(
    <BriefSubscriptionForm
      brief={brief}
      busy={false}
      error={null}
      onCreate={onCreate}
      onCancel={vi.fn()}
    />,
  );
  const time = screen.getByLabelText('Local time');
  const form = screen.getByRole('form', { name: 'Subscribe to Research Brief' });
  fireEvent.change(time, { target: { value: '' } });
  fireEvent.submit(form);
  expect(onCreate).not.toHaveBeenCalled();
  expect(screen.getByRole('alert')).toHaveTextContent('Choose a valid local time.');
  fireEvent.change(time, { target: { value: '00:00' } });
  fireEvent.submit(form);
  expect(onCreate).toHaveBeenCalledWith(
    expect.objectContaining({ local_hour: 0, local_minute: 0 }),
  );
});

it('shows a rejected timezone beside its field and keeps a plain message working', () => {
  const rejection = new ApiError(422, 'validation_error', 'The request is invalid.', {
    timezone: 'Unknown timezone.',
    brief_revision: 'Revision is stale.',
  });
  const { rerender } = render(
    <BriefSubscriptionForm
      brief={brief}
      busy={false}
      error={rejection}
      onCreate={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  const timezone = screen.getByLabelText('IANA timezone');
  expect(timezone).toHaveAttribute('aria-invalid', 'true');
  expect(timezone).toHaveAccessibleDescription('Unknown timezone.');
  const summary = screen.getByRole('alert', { name: 'Check these fields and try again:' });
  expect(summary).toHaveFocus();
  expect(summary).toHaveTextContent('Brief revision: Revision is stale.');
  fireEvent.click(screen.getByRole('link', { name: 'IANA timezone: Unknown timezone.' }));
  expect(timezone).toHaveFocus();

  rerender(
    <BriefSubscriptionForm
      brief={brief}
      busy={false}
      error="The saved subscription referenced a different brief revision."
      onCreate={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  expect(screen.getByRole('alert')).toHaveTextContent(
    'The saved subscription referenced a different brief revision.',
  );
});
