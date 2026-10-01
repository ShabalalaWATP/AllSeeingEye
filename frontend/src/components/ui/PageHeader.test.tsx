import { render, screen } from '@testing-library/react';
import { createRef } from 'react';
import { describe, expect, it } from 'vitest';

import { PageHeader } from './PageHeader';

describe('PageHeader', () => {
  it('gives each page type one heading size', () => {
    const { rerender } = render(<PageHeader title="Research" />);
    expect(screen.getByRole('heading', { level: 1, name: 'Research' })).toHaveClass('text-3xl');
    rerender(<PageHeader type="record" title="Aviation" />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveClass('text-xl');
    rerender(<PageHeader type="status" title="Page not found" />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveClass('text-2xl');
  });

  it('introduces the title with its eyebrow, description, extras and actions', () => {
    render(
      <PageHeader
        title="Teams"
        eyebrow="Shared workspaces"
        eyebrowTone="cyan"
        back={<a href="/">Back</a>}
        titleAside={<span>Archived</span>}
        description="Shared research and a team board."
        actions={<button type="button">Create a team</button>}
      >
        <a href="/reports/saved">All saved reports</a>
      </PageHeader>,
    );
    const header = screen.getByRole('banner');
    expect(header).toHaveTextContent(
      'BackShared workspacesTeamsArchivedShared research and a team board.All saved reportsCreate a team',
    );
    expect(screen.getByText('Shared workspaces')).toHaveClass('text-cyan', 'text-2xs');
  });

  it('lets the page move focus to its heading and name a region with it', () => {
    const ref = createRef<HTMLHeadingElement>();
    render(
      <section aria-labelledby="mfa-title">
        <PageHeader as="div" title="Security" headingId="mfa-title" headingRef={ref} focusable />
      </section>,
    );
    expect(screen.getByRole('region', { name: 'Security' })).toBeInTheDocument();
    expect(screen.queryByRole('banner')).not.toBeInTheDocument();
    ref.current?.focus();
    expect(screen.getByRole('heading', { level: 1 })).toHaveFocus();
    expect(screen.getByRole('heading', { level: 1 })).toHaveAttribute('tabindex', '-1');
  });

  it('is not focusable unless asked', () => {
    render(<PageHeader title="Research" />);
    expect(screen.getByRole('heading', { level: 1 })).not.toHaveAttribute('tabindex');
  });
});
