import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

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
