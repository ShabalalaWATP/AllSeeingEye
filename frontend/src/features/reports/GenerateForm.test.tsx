import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';

import type { ReportRequest } from '@/lib/api/reports';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { reportTemplates } from '@/test/fixtures.reports';
import { photoWorkspaces } from '@/test/photoGeolocationFixture';

import { GenerateForm } from './GenerateForm';

beforeEach(() => {
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
});

function mount() {
  const onSubmit = vi.fn<(request: ReportRequest) => void>();
  render(
    <GenerateForm
      templates={reportTemplates}
      plans={[]}
      workspaces={photoWorkspaces()}
      countries={[]}
      conflicts={[]}
      hazards={[]}
      busy={false}
      error={null}
      onSubmit={onSubmit}
    />,
  );
  return { user: userEvent.setup(), onSubmit };
}

it('does not send a hidden question typed for another product', async () => {
  const { user, onSubmit } = mount();
  await user.selectOptions(screen.getByLabelText('Product'), 'ask');
  await user.type(screen.getByLabelText('Question'), 'What next?');
  await user.selectOptions(screen.getByLabelText('Product'), 'intsum');
  expect(screen.queryByLabelText('Question')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Generate' }));
  expect(onSubmit).toHaveBeenCalledOnce();
  expect(onSubmit.mock.calls[0]?.[0]).toMatchObject({ template: 'intsum' });
  expect(onSubmit.mock.calls[0]?.[0]).not.toHaveProperty('question');

  await user.selectOptions(screen.getByLabelText('Product'), 'ask');
  expect(screen.getByLabelText('Question')).toHaveValue('What next?');
  await user.click(screen.getByRole('button', { name: 'Generate' }));
  expect(onSubmit.mock.calls[1]?.[0]).toMatchObject({ template: 'ask', question: 'What next?' });
});
