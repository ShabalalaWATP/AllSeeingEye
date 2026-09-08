import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { ConflictSourceProvenance } from './ConflictSourceProvenance';

it('shows original ReliefWeb publishers and a safe link to the original publication', () => {
  render(
    <ConflictSourceProvenance
      event={liveEvent({
        attributes: {
          original_publishers: 'OCHA, UNHCR',
          original_url: 'https://example.org/original',
        },
      })}
    />,
  );
  expect(screen.getByText('OCHA, UNHCR')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'https://example.org/original' })).toHaveAttribute(
    'href',
    'https://example.org/original',
  );
  expect(screen.getByText(/independence is not established/)).toBeInTheDocument();
});

it('shows UCDP article attribution as text and rejects non-http original source links', () => {
  render(
    <ConflictSourceProvenance
      event={liveEvent({
        attributes: {
          source_articles: 'Wire service, 14 July: reported incident',
          source_original: 'javascript:alert(1)',
        },
      })}
    />,
  );
  expect(screen.getByText('Wire service, 14 July: reported incident')).toBeInTheDocument();
  expect(screen.getByText('javascript:alert(1)')).toBeInTheDocument();
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
});

it('bounds long citations and renders markup as literal text', () => {
  const long = `https://example.org/${'a'.repeat(3_000)}`;
  render(
    <ConflictSourceProvenance
      event={liveEvent({
        attributes: { source_articles: long, source_original: '<script>alert(1)</script>' },
      })}
    />,
  );
  expect(screen.getByText(/truncated/).textContent.length).toBeLessThan(830);
  expect(screen.getByText('<script>alert(1)</script>')).toBeInTheDocument();
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
});

it('omits absent, empty and non-text attribution without inventing publishers', () => {
  const { container } = render(
    <ConflictSourceProvenance
      event={liveEvent({
        attributes: { original_publishers: ' ', source_articles: false, source_original: null },
      })}
    />,
  );
  expect(container).toBeEmptyDOMElement();
});
