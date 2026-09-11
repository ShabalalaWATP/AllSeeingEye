import { act, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { mockMatchMedia, setVisibility } from '@/test/env';

import { AssistantEye } from './AssistantEye';

describe('AssistantEye', () => {
  it('uses the original transparent animation with pupil movement at 24 fps', () => {
    const { container } = render(<AssistantEye className="assistant-launcher-eye" />);
    const eye = screen.getByTestId('evil-eye');
    expect(eye).toHaveAttribute('data-transparent', 'true');
    expect(eye).toHaveAttribute('data-max-fps', '24');
    expect(eye).toHaveAttribute('data-flame-speed', '1');
    expect(eye).toHaveAttribute('data-pupil-follow', '1');
    expect(container.firstChild).toHaveAttribute('aria-hidden', 'true');
    expect(container.firstChild).toHaveClass('assistant-launcher-eye');
  });

  it('stops while the page is hidden and resumes on return', () => {
    render(<AssistantEye />);
    act(() => setVisibility('hidden'));
    expect(screen.getByTestId('evil-eye')).toHaveAttribute('data-paused', 'true');
    act(() => setVisibility('visible'));
    expect(screen.getByTestId('evil-eye')).toHaveAttribute('data-paused', 'false');
  });

  it('holds the flames and pupil still when reduced motion is requested', () => {
    mockMatchMedia(true);
    render(<AssistantEye />);
    const eye = screen.getByTestId('evil-eye');
    expect(eye).toHaveAttribute('data-flame-speed', '0');
    expect(eye).toHaveAttribute('data-pupil-follow', '0');
    expect(eye).toHaveAttribute('data-max-fps', '1');
  });
});
