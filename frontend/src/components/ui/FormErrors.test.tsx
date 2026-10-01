import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import { useFieldErrors } from '@/lib/api/fieldErrors';

import { TextField } from './Field';
import { FormErrors } from './FormErrors';

function Form({ error }: { error: unknown }) {
  const errors = useFieldErrors(error, {
    name: 'Name',
    countries: { label: 'Nations', target: 'nations-step' },
  });
  return (
    <form aria-label="Example">
      <FormErrors errors={errors} />
      <TextField label="Name" {...errors.field('name')} />
      <details>
        <summary>More</summary>
        <section id="nations-step">
          <h3>Nations</h3>
          <input aria-label="Nation search" />
        </section>
      </details>
    </form>
  );
}

const invalid = (fields: Record<string, string>) =>
  new ApiError(422, 'validation_error', 'The request is invalid.', fields);

describe('FormErrors', () => {
  it('renders nothing without an error', () => {
    render(<Form error={null} />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('falls back to the safe generic message without field reasons', () => {
    render(
      <Form error={new ApiError(500, 'internal_error', 'Something went wrong on our side.')} />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong on our side.');
    expect(screen.getByLabelText('Name')).not.toHaveAttribute('aria-invalid');
  });

  it('links each reason to its field, marks the field invalid and focuses the summary', async () => {
    const user = userEvent.setup();
    render(<Form error={invalid({ name: 'Too long.', 'countries.2': 'Unknown nation.' })} />);
    const summary = screen.getByRole('alert', { name: 'Check these fields and try again:' });
    expect(summary).toHaveFocus();
    expect(summary).not.toHaveTextContent('The request is invalid.');

    const name = screen.getByLabelText('Name');
    expect(name).toHaveAttribute('aria-invalid', 'true');
    expect(name).toHaveAccessibleDescription('Too long.');

    await user.click(screen.getByRole('link', { name: 'Name: Too long.' }));
    expect(name).toHaveFocus();
    await user.click(screen.getByRole('link', { name: 'Nations: Unknown nation.' }));
    expect(screen.getByLabelText('Nation search')).toHaveFocus();
    expect(screen.getByText('More').closest('details')).toHaveAttribute('open');
  });

  it('keeps unknown paths and uses the generic heading only when nothing matched', () => {
    render(<Form error={invalid({ 'research_area.geometry': 'Invalid shape.' })} />);
    const summary = screen.getByRole('alert', { name: 'The request is invalid.' });
    expect(summary).toHaveTextContent('Research area geometry: Invalid shape.');
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('lists unknown paths beside matched ones', () => {
    render(<Form error={invalid({ name: 'Required.', cooldown_minutes: 'Too small.' })} />);
    const summary = screen.getByRole('alert', { name: 'Check these fields and try again:' });
    expect(summary).toHaveTextContent('Name: Required.');
    expect(summary).toHaveTextContent('Cooldown minutes: Too small.');
  });

  it('renders reasons as text, never as markup', () => {
    render(<Form error={invalid({ name: '<img src=x onerror=alert(1)>' })} />);
    expect(screen.getByRole('link', { name: 'Name: <img src=x onerror=alert(1)>' })).toBeVisible();
    expect(document.querySelector('img')).toBeNull();
  });
});
