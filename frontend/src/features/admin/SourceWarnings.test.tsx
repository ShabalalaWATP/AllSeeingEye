import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { source, sourceHealth } from '@/test/fixtures';
import { sourceHealthSchema } from '@/lib/api/eventSchemas';
import { SourceRow } from './SourceRow';
import { summariseSources } from './overview/overviewSummaries';

it('counts a successful sampled feed as live and displays its coverage warning', () => {
  const health = sourceHealthSchema.parse({
    ...sourceHealth({ status: 'healthy', consecutive_failures: 0, last_error: null }),
    warning: 'Limited sampled coverage',
  });
  const sampled = source({ health });
  expect(summariseSources([sampled])).toMatchObject({ healthy: 1, failing: 0 });
  render(
    <table>
      <tbody>
        <SourceRow source={sampled} now={Date.now()} onReset={vi.fn()} onActivation={vi.fn()} />
      </tbody>
    </table>,
  );
  expect(screen.getByText('Live with warning')).toBeVisible();
  expect(screen.getByText('Limited sampled coverage')).toBeVisible();
  expect(screen.queryByText(/failed in a row/)).not.toBeInTheDocument();
});
