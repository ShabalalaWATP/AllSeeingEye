import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderApp } from '@/test/render';

vi.mock('virtual:policy-approval', () => ({ default: true }));
vi.mock('./service.json', () => ({
  default: {
    businessDisclosure: 'Fixture business address <script>untrusted()</script>',
    businessAddress: 'Fixture street <b>1</b>',
    accessibilityContact: 'Fixture access contact <a href="javascript:alert(1)">contact</a>',
  },
}));
const section = (id: string, text: string) => ({ id, title: `Fixture ${id}`, paragraphs: [text] });
vi.mock('./terms.json', () => ({
  default: {
    version: '2026-10-18',
    sections: [section('terms', 'Fixture terms <img src="https://example.test/tracker">')],
  },
}));
vi.mock('./acceptable-use.json', () => ({
  default: { sections: [section('use', 'Fixture use <iframe src="https://example.test">')] },
}));
vi.mock('./accessibility.json', () => ({
  default: {
    lastReviewed: '2026-10-18',
    nextReview: '2027-04-18',
    sections: [section('feedback', 'Fixture statement')],
  },
}));
vi.mock('./privacy.json', async (original) => {
  const actual = await original<{ default: { operator: Record<string, string | null> } }>();
  return {
    default: {
      ...actual.default,
      operator: {
        ...actual.default.operator,
        controllerName: 'Fixture operator',
        controllerContact: 'operator@example.test',
        jurisdiction: 'Fixture jurisdiction',
      },
    },
  };
});

describe('approved installation policy text', () => {
  it.each([
    ['/terms', 'Terms', 'Fixture terms <img src="https://example.test/tracker">'],
    ['/acceptable-use', 'Acceptable Use Policy', 'Fixture use <iframe src="https://example.test">'],
    ['/business', 'Business details', 'Fixture business address <script>untrusted()</script>'],
    [
      '/accessibility',
      'Accessibility',
      'Fixture access contact <a href="javascript:alert(1)">contact</a>',
    ],
  ])('renders approved %s values as text, without a draft warning', async (path, title, text) => {
    const { container } = renderApp(path, 'anonymous');
    await screen.findByRole('heading', { level: 1, name: title });
    expect(screen.getByText(text)).toBeInTheDocument();
    expect(screen.queryByLabelText('Draft notice')).not.toBeInTheDocument();
    expect(screen.queryByText(/Decision needed/)).not.toBeInTheDocument();
    expect(container.querySelector('script,img,iframe,b,a[href^="javascript:"]')).toBeNull();
    if (path === '/business') {
      expect(screen.getByText('Fixture operator')).toBeInTheDocument();
      expect(screen.getByText('operator@example.test')).toBeInTheDocument();
      expect(screen.getByText('Fixture jurisdiction')).toBeInTheDocument();
      expect(screen.getByText('Fixture street <b>1</b>')).toBeInTheDocument();
      expect(screen.queryByText(/Not yet confirmed by the operator/)).not.toBeInTheDocument();
    }
  });
});
