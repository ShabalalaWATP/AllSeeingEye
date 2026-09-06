import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { ReportOptions } from './ReportOptions';

it('shows the PDF limitation when selecting an unsupported narrative script and clears it for English', () => {
  const props = { style: 'assessment' as const, onLanguage: vi.fn(), onStyle: vi.fn() };
  const { rerender } = render(<ReportOptions {...props} language="ar" />);
  expect(screen.getByRole('status')).toHaveTextContent(
    'cannot currently display Arabic text correctly',
  );
  expect(screen.getByRole('status')).toHaveTextContent('Choose DOCX or Markdown');
  rerender(<ReportOptions {...props} language="zh" />);
  expect(screen.getByRole('status')).toHaveTextContent(
    'cannot currently display Chinese text correctly',
  );
  rerender(<ReportOptions {...props} language="en" />);
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});
