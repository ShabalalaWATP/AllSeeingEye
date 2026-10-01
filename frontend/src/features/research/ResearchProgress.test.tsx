import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import { ResearchProgress } from './ResearchProgress';

describe('research progress display', () => {
  it.each([
    ['running', 'Starting research'],
    ['completed', 'Report saved'],
  ] as const)('shows %s without claiming an unreported server stage', (outcome, title) => {
    render(
      <ResearchProgress
        snapshot={{ stage: null, outcome, unavailable: false }}
        active={false}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByRole('status')).toHaveTextContent(title);
  });
  it('renders nothing before a run', () => {
    const { container } = render(
      <ResearchProgress snapshot={null} active={false} onCancel={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
  it('names the real stage, exposes cancellation and does not render a percentage', () => {
    const cancel = vi.fn();
    render(
      <ResearchProgress
        snapshot={{ stage: 'validating', outcome: 'running', unavailable: true }}
        active
        onCancel={cancel}
      />,
    );
    expect(screen.getByRole('status')).toHaveTextContent('Checking the report');
    expect(screen.getByText(/Live progress is unavailable/)).toBeVisible();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel research' }));
    expect(cancel).toHaveBeenCalledOnce();
  });
  it.each(['cancelled', 'failed'] as const)('explains uncertain saving after %s', (outcome) => {
    render(
      <MemoryRouter>
        <ResearchProgress
          snapshot={{ stage: 'saving', outcome, unavailable: false }}
          active={false}
          onCancel={vi.fn()}
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: 'Check Reports' })).toHaveAttribute('href', '/reports');
    expect(screen.getByText(/A report being saved may still complete/)).toBeVisible();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
