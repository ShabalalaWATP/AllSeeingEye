import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { webResearchSchema } from '@/lib/api/webResearch';
import type { WebResearch } from '@/lib/api/webResearch';

import { FreshWebContext } from './FreshWebContext';

const record: WebResearch = {
  status: 'completed',
  explanation: 'A live web search returned discovery references.',
  retrieved_at: '2026-09-11T12:00:00Z',
  requested_model: 'configured-model',
  returned_model: 'returned-model',
  profile_id: null,
  profile_revision: 1,
  synthesis: 'A 🌍 clue. <script>untrusted()</script>',
  citations: [
    {
      url: 'https://example.org/article',
      title: 'Original reference',
      start_index: 0,
      end_index: 9,
    },
  ],
  consulted_urls: ['https://example.org/article'],
  tool_calls: 1,
  request_count: 1,
  prompt_tokens: 100,
  completion_tokens: 50,
  latency_ms: 20,
  policy_version: 'ase-web-context-v1',
  notice: 'AI-generated web context, not independently verified evidence.',
};

describe('fresh web context', () => {
  it('keeps generated context separate and safely links codepoint-based citations', () => {
    const { container } = render(<FreshWebContext record={record} />);
    expect(screen.getByRole('region', { name: 'Fresh web context' })).toBeInTheDocument();
    expect(screen.getByText(record.notice)).toBeInTheDocument();
    const reference = screen.getByRole('link', { name: 'Web reference 1: Original reference' });
    expect(reference.previousSibling?.textContent).toBe('A 🌍 clue.');
    expect(reference).toHaveAttribute('href', 'https://example.org/article');
    expect(reference).toHaveAttribute('rel', 'noopener noreferrer');
    expect(container.querySelector('script')).toBeNull();
    expect(container.textContent).toContain('<script>untrusted()</script>');
  });

  it('explains unavailable search without presenting synthetic results', () => {
    render(
      <FreshWebContext
        record={{
          ...record,
          status: 'unavailable',
          synthesis: '',
          citations: [],
          explanation: 'Configure an enabled OpenAI search connection.',
          tool_calls: 0,
          request_count: 0,
        }}
      />,
    );
    expect(screen.getByText('Configure an enabled OpenAI search connection.')).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Web references' })).not.toBeInTheDocument();
  });

  it('rejects executable or credential-bearing returned URLs at the API boundary', () => {
    for (const url of ['javascript:alert(1)', 'https://user:secret@example.org/']) {
      expect(
        webResearchSchema.safeParse({ ...record, citations: [{ ...record.citations[0], url }] })
          .success,
      ).toBe(false);
    }
    expect(webResearchSchema.safeParse(record).success).toBe(true);
  });

  it('keeps legacy reports without web research readable', () => {
    const { container } = render(<FreshWebContext record={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});
