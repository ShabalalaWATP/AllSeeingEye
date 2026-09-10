import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { RfLinkAdvice } from './RfLinkAdvice';
import { rfLinkAdvice } from '@/lib/map/rfLinkAdvice';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';

vi.mock('@/lib/map/rfLinkAdvice', () => ({ rfLinkAdvice: vi.fn() }));
const analysis = {} as Extract<RfAnalysis, { kind: 'terrain' }>;

it('explains an automatic height scenario without presenting it as a measured or applied change', () => {
  vi.mocked(rfLinkAdvice).mockReturnValue({
    kind: 'height',
    site: 'transmitter',
    heightM: 16,
    addedM: 6,
    planningMarginDb: -3,
    status: 'risk',
  });
  render(<RfLinkAdvice analysis={analysis} />);
  expect(screen.getByLabelText('Automatic link improvement check')).toHaveTextContent(
    '16 m above ground',
  );
  expect(screen.getByText(/still fall short/)).toBeVisible();
  expect(screen.getByText(/same coarse terrain/)).toBeVisible();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
});

it('shows a power shortfall and omits unnecessary advice for a passing link', () => {
  vi.mocked(rfLinkAdvice).mockReturnValue({ kind: 'budget', shortfallDb: 4.2 });
  const { rerender } = render(<RfLinkAdvice analysis={analysis} />);
  expect(screen.getByText(/another 4.2 dB/)).toBeVisible();
  vi.mocked(rfLinkAdvice).mockReturnValue(null);
  rerender(<RfLinkAdvice analysis={analysis} />);
  expect(screen.queryByLabelText('Automatic link improvement check')).not.toBeInTheDocument();
});
