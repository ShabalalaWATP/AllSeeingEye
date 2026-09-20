import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { adminUser, plainUser } from '@/test/fixtures';
import { applySession } from '@/test/render';
import type { LlmProfile } from '@/lib/api/llm';
import { ModelSetupWizard } from './ModelSetupWizard';
import { binding, draft, installConnections, team } from './llmTestFixtures';

export const secondTeam = {
  ...team,
  id: '88888888-8888-4888-8888-888888888888',
  name: 'Second team',
};

/** jsdom does not implement the native dialog top layer. */
export function mockModelSetupDialog() {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
    configurable: true,
    value(this: HTMLDialogElement) {
      this.open = true;
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', {
    configurable: true,
    value(this: HTMLDialogElement) {
      this.open = false;
    },
  });
}

export async function openWizard(initial?: LlmProfile) {
  const state = installConnections(initial ? [initial] : []);
  applySession('admin');
  const onSaved = vi.fn();
  const onApply = vi.fn(() => Promise.resolve());
  const onClose = vi.fn();
  function Harness() {
    const [open, setOpen] = useState(false);
    return (
      <>
        <button onClick={() => setOpen(true)}>Open model setup</button>
        {open && (
          <ModelSetupWizard
            {...(initial ? { initial } : {})}
            profiles={state.profiles}
            teams={[team, secondTeam]}
            users={[plainUser, adminUser]}
            connections={[binding(draft())]}
            onSaved={onSaved}
            onApply={onApply}
            onClose={() => {
              onClose();
              setOpen(false);
            }}
          />
        )}
      </>
    );
  }
  const user = userEvent.setup();
  const view = render(<Harness />);
  await user.click(screen.getByRole('button', { name: 'Open model setup' }));
  return { ...view, user, state, onSaved, onApply, onClose };
}

export async function advanceToTest(view: Awaited<ReturnType<typeof openWizard>>) {
  await view.user.type(screen.getByLabelText('Connection name'), 'Research model');
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  await view.user.type(screen.getByLabelText('API key'), 'synthetic-test-key');
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  await view.user.selectOptions(await screen.findByLabelText('Account model'), 'gpt-5.6-luna');
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  await view.user.selectOptions(screen.getByLabelText('Reasoning level'), 'max');
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
}

export async function advanceToAudience(view: Awaited<ReturnType<typeof openWizard>>) {
  await advanceToTest(view);
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  await screen.findByText(/Connection test passed/);
  await view.user.click(screen.getByRole('button', { name: 'Choose audience' }));
}
