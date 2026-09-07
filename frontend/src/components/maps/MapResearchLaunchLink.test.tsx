import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { savedMapFixture } from '@/test/fixtures.savedMaps';
import { MapResearchLaunchLink } from './MapResearchLaunchLink';

it('links the exact immutable saved area revision', () => {
  render(<MapResearchLaunchLink saved={savedMapFixture} changed={false} />);
  expect(screen.getByRole('link')).toHaveAttribute(
    'href',
    '/research?map_view=view-1&map_revision=revision-1',
  );
});
it('blocks launch while an area draft or applied area is unsaved', () => {
  render(<MapResearchLaunchLink saved={savedMapFixture} changed />);
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(screen.getByText(/save your area changes/)).toBeInTheDocument();
});
it('requires a saved area before launch', () => {
  render(<MapResearchLaunchLink saved={null} changed={false} />);
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(screen.getByText(/Save a map revision with an area/)).toBeInTheDocument();
});
