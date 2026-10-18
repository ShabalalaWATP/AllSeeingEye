import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import { server } from '@/test/server';

import { StoryMotionContext } from '../motion/useStoryMotion';
import { ContactChapter } from './ContactChapter';

async function sendEnquiry(still: boolean) {
  server.use(
    http.post('/api/enquiries', () => HttpResponse.json({ message: 'ok' }, { status: 202 })),
  );
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <StoryMotionContext.Provider value={{ still, idle: still }}>
        <ContactChapter enquiriesEnabled />
      </StoryMotionContext.Provider>
    </MemoryRouter>,
  );
  expect(screen.getByTestId('contact-eye')).not.toHaveAttribute('data-closed');
  await user.type(screen.getByRole('textbox', { name: 'Name' }), 'Example Visitor');
  await user.type(screen.getByRole('textbox', { name: 'Work email' }), 'visitor@example.test');
  await user.type(screen.getByRole('textbox', { name: 'Organisation' }), 'Example Organisation');
  await user.selectOptions(screen.getByLabelText('Deployment interest'), 'own_cloud');
  await user.selectOptions(screen.getByLabelText('Expected users'), '11_50');
  await user.click(screen.getByRole('checkbox', { name: /I have read/ }));
  await user.click(screen.getByRole('button', { name: 'Send enquiry' }));
  await screen.findByText(/Your enquiry has been received/);
}

describe('closing scene', () => {
  it('closes the Eye softly once an enquiry is received', async () => {
    await sendEnquiry(false);
    expect(screen.getByTestId('contact-eye')).toHaveAttribute('data-closed', 'true');
  });

  it('leaves the Eye unchanged while the story is still', async () => {
    await sendEnquiry(true);
    expect(screen.getByTestId('contact-eye')).not.toHaveAttribute('data-closed');
  });
});
