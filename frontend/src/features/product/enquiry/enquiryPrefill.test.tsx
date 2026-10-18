import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { useState } from 'react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import { server } from '@/test/server';

import { EnterpriseEnquiryForm } from './EnterpriseEnquiryForm';
import {
  createPrefillChannel,
  EnquiryPrefillContext,
  mergePrefill,
  PREFILL_NOTICES,
  useEnquiryPrefill,
} from './enquiryPrefill';

const ESTIMATE = 'Self-hosting running-cost estimate. This is an estimate, not a quote.';

function Offer({ text = ESTIMATE }: { text?: string }) {
  const prefill = useEnquiryPrefill();
  return (
    <button type="button" onClick={() => prefill.offer(text)}>
      Offer {text.length}
    </button>
  );
}

function Harness({ onSubmitted }: { onSubmitted?: () => void }) {
  const [channel] = useState(createPrefillChannel);
  return (
    <MemoryRouter>
      <EnquiryPrefillContext.Provider value={{ ...channel, available: true }}>
        <Offer />
        <Offer text={'x'.repeat(1990)} />
        <EnterpriseEnquiryForm onSubmitted={onSubmitted} />
      </EnquiryPrefillContext.Provider>
    </MemoryRouter>
  );
}

const message = () => screen.getByLabelText('Message (optional)');

describe('estimate hand-off to the enquiry message', () => {
  it('fills an empty message, focuses it and submits nothing', async () => {
    const post = vi.fn();
    server.use(
      http.post('/api/enquiries', () => {
        post();
        return HttpResponse.json({ message: 'ok' }, { status: 202 });
      }),
    );
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole('button', { name: `Offer ${ESTIMATE.length}` }));
    expect(message()).toHaveValue(ESTIMATE);
    expect(message()).toHaveFocus();
    expect(screen.getByText(PREFILL_NOTICES.filled)).toHaveAttribute('role', 'status');
    expect(post).not.toHaveBeenCalled();
  });

  it('never replaces text the visitor has typed', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.type(message(), 'Our own words.');
    await user.click(screen.getByRole('button', { name: `Offer ${ESTIMATE.length}` }));
    expect(message()).toHaveValue(`Our own words.\n\n${ESTIMATE}`);
    expect(screen.getByText(PREFILL_NOTICES.appended)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: `Offer ${ESTIMATE.length}` }));
    expect(message()).toHaveValue(`Our own words.\n\n${ESTIMATE}`);
    expect(screen.getByText(PREFILL_NOTICES.unchanged)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Offer 1990' }));
    expect(message()).toHaveValue(`Our own words.\n\n${ESTIMATE}`);
    expect(screen.getByText(PREFILL_NOTICES.too_long)).toBeInTheDocument();
  });

  it('reports a received enquiry and then only focuses the confirmation', async () => {
    server.use(
      http.post('/api/enquiries', () => HttpResponse.json({ message: 'ok' }, { status: 202 })),
    );
    const onSubmitted = vi.fn();
    const user = userEvent.setup();
    render(<Harness onSubmitted={onSubmitted} />);
    await user.type(screen.getByRole('textbox', { name: 'Name' }), 'Example Visitor');
    await user.type(screen.getByRole('textbox', { name: 'Work email' }), 'visitor@example.test');
    await user.type(screen.getByRole('textbox', { name: 'Organisation' }), 'Example Organisation');
    await user.selectOptions(screen.getByLabelText('Deployment interest'), 'own_cloud');
    await user.selectOptions(screen.getByLabelText('Expected users'), '11_50');
    await user.click(screen.getByRole('checkbox', { name: /I have read/ }));
    expect(onSubmitted).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Send enquiry' }));
    const confirmation = await screen.findByText(/Your enquiry has been received/);
    expect(onSubmitted).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole('button', { name: `Offer ${ESTIMATE.length}` }));
    expect(confirmation).toHaveFocus();
    expect(screen.queryByRole('textbox')).toBeNull();
  });
});

describe('message merging', () => {
  it('fills blank messages and bounds the result', () => {
    expect(mergePrefill('  ', 'abc')).toEqual({ message: 'abc', outcome: 'filled' });
    expect(mergePrefill('', 'abcdef', 3)).toEqual({ message: 'abc', outcome: 'filled' });
    expect(mergePrefill('note  ', 'abc')).toEqual({ message: 'note\n\nabc', outcome: 'appended' });
    expect(mergePrefill('note', 'abc', 6)).toEqual({ message: 'note', outcome: 'too_long' });
  });

  it('ignores offers when no form is listening', () => {
    const channel = createPrefillChannel();
    const receiver = vi.fn();
    const stop = channel.receive(receiver);
    channel.offer('one');
    stop();
    channel.offer('two');
    expect(receiver).toHaveBeenCalledTimes(1);
    // An older registration never removes a newer one.
    const newer = vi.fn();
    channel.receive(newer);
    stop();
    channel.offer('three');
    expect(newer).toHaveBeenCalledWith('three');
  });
});
