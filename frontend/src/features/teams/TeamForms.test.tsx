import { fireEvent, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { AddMemberForm, TeamNameForm } from './TeamForms';

describe('TeamNameForm', () => {
  it('ignores a blank submission and trims a new team', async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<TeamNameForm busy={false} onSave={onSave} />);
    fireEvent.submit(screen.getByRole('form', { name: 'Create team' }));
    expect(onSave).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText('New team name'), '  Desk  ');
    await user.click(screen.getByRole('button', { name: 'Create team' }));
    expect(onSave).toHaveBeenCalledWith('Desk', undefined);
  });

  it('only enables renaming after a change', async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<TeamNameForm name="Desk" description={null} busy={false} onSave={onSave} />);
    const save = screen.getByRole('button', { name: 'Save name' });
    expect(save).toBeDisabled();
    await user.type(screen.getByLabelText(/Team description/), 'Purpose');
    await user.click(save);
    expect(onSave).toHaveBeenCalledWith('Desk', 'Purpose');
  });
});

describe('AddMemberForm', () => {
  it('adds a member without a role choice when manager roles are not allowed', async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<AddMemberForm admin={false} busy={false} onSave={onSave} />);
    expect(screen.queryByLabelText('Team role')).not.toBeInTheDocument();
    expect(screen.queryByText(/Direct adds are recorded/)).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(/Account email/), ' person@example.com ');
    await user.click(screen.getByRole('button', { name: 'Add member' }));
    expect(onSave).toHaveBeenCalledWith({ email: 'person@example.com', role: 'member' });
  });

  it('lets administrators switch the role back to member', async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<AddMemberForm admin busy={false} onSave={onSave} />);
    expect(screen.getByText(/Direct adds are recorded/)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Team role'), 'manager');
    await user.selectOptions(screen.getByLabelText('Team role'), 'member');
    await user.type(screen.getByLabelText(/Account email/), 'lead@example.com');
    await user.click(screen.getByRole('button', { name: 'Add member' }));
    expect(onSave).toHaveBeenCalledWith({ email: 'lead@example.com', role: 'member' });
  });
});
