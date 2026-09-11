import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { MaritimeAttribution } from './MaritimeAttribution';

it('credits displayed BarentsWatch data and clears the credit when its layer or scope is hidden', () => {
  const records = [liveEvent({ source_id: 'barentswatch_ais', category: 'maritime' })];
  const { rerender } = render(<MaritimeAttribution events={records} hidden={false} />);
  expect(screen.getByRole('link', { name: /Data delivered by BarentsWatch/ })).toHaveAttribute(
    'href',
    'https://www.barentswatch.no/en/articles/api-terms-and-conditions/',
  );
  expect(screen.getByRole('link')).toHaveTextContent('Norwegian Coastal Administration');
  rerender(<MaritimeAttribution events={records} hidden />);
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  rerender(<MaritimeAttribution events={[]} hidden={false} />);
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  rerender(<MaritimeAttribution events={[liveEvent({ source_id: 'aisstream' })]} hidden={false} />);
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
});
