import { render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { ReportOptions } from './ReportOptions';

it('shows the PDF limitation for Arabic and clears it for supported output', async () => {
  const props = { style: 'assessment' as const, onLanguage: vi.fn(), onStyle: vi.fn() };
  const { rerender } = render(<ReportOptions {...props} language="ar" />);
  expect(screen.getByText(/cannot currently display Arabic text correctly/)).toBeInTheDocument();
  rerender(<ReportOptions {...props} language="zh" />);
  await waitFor(() =>
    expect(screen.queryByText(/cannot currently display Chinese/)).not.toBeInTheDocument(),
  );
  rerender(<ReportOptions {...props} language="en" />);
  expect(screen.queryByText(/PDF downloads cannot/)).not.toBeInTheDocument();
});
