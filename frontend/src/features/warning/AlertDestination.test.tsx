import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { expect, it } from 'vitest';
import { AlertDestination } from './AlertDestination';
it('links alerts to their exact historical transition and never substitutes the latest report', () => {
  const { rerender } = render(
    <MemoryRouter>
      <AlertDestination monitorId="monitor-1" transitionId="old-transition" reportId="report-1" />
    </MemoryRouter>,
  );
  expect(screen.getByRole('link')).toHaveAttribute(
    'href',
    '/annotation-monitors/monitor-1/transitions/old-transition',
  );
  rerender(
    <MemoryRouter>
      <AlertDestination monitorId="monitor-1" transitionId={null} reportId="report-1" />
    </MemoryRouter>,
  );
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(screen.getByText('Exact annotation transition unavailable')).toBeInTheDocument();
  rerender(
    <MemoryRouter>
      <AlertDestination monitorId={null} transitionId={null} reportId="report-1" />
    </MemoryRouter>,
  );
  expect(screen.getByRole('link', { name: 'Report' })).toHaveAttribute('href', '/reports/report-1');
  rerender(
    <MemoryRouter>
      <AlertDestination monitorId={null} transitionId={null} reportId={null} />
    </MemoryRouter>,
  );
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
});
