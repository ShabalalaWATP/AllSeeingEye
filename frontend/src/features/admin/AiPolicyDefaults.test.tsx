import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { aiDefaults, aiPolicy } from '@/test/fixtures.aiUsage';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { AiPolicyDefaults } from './AiPolicyDefaults';

function mount(onApplied = vi.fn()) {
  const user = userEvent.setup();
  render(<AiPolicyDefaults onApplied={onApplied} />);
  return { user, onApplied };
}

describe('AiPolicyDefaults', () => {
  it('says plainly that nothing is enforced until a policy exists', async () => {
    server.use(
      http.get('/api/admin/ai-usage/defaults', () => HttpResponse.json(aiDefaults())),
    );
    mount();
    expect(
      await screen.findByText(
        'No policy is active. Usage is recorded for observation and nothing is enforced.',
      ),
    ).toBeInTheDocument();
  });

  it('compares the suggestion against the measured daily usage', async () => {
    server.use(http.get('/api/admin/ai-usage/defaults', () => HttpResponse.json(aiDefaults())));
    mount();
    // 300,000 a day against a measured 194,000 a day is 1.5 times, not a wide margin.
    expect(await screen.findByText(/about 1.5 times that average/)).toBeInTheDocument();
    expect(screen.getByText(/969,000 tokens this month/)).toBeInTheDocument();
  });

  it('applies only the missing policies and never overwrites an existing one', async () => {
    let applied = 0;
    server.use(
      http.get('/api/admin/ai-usage/defaults', () => HttpResponse.json(aiDefaults())),
      http.post('/api/admin/ai-usage/defaults', () => {
        applied += 1;
        return HttpResponse.json({ created: [aiPolicy({ period: 'day' })] }, { status: 201 });
      }),
    );
    const { user, onApplied } = mount();
    const button = await screen.findByRole('button', { name: 'Apply 1 suggested policies' });
    expect(screen.getByText('Already configured, kept as is')).toBeInTheDocument();
    await user.click(button);
    expect(await screen.findByText(/1 policies were created/)).toBeInTheDocument();
    expect(applied).toBe(1);
    expect(onApplied).toHaveBeenCalledTimes(1);
  });

  it('says when a site is already enforcing and nothing is left to create', async () => {
    const everything = aiDefaults({
      enforcing: true,
      items: aiDefaults().items.map((item) => ({ ...item, already_configured: true })),
    });
    server.use(http.get('/api/admin/ai-usage/defaults', () => HttpResponse.json(everything)));
    mount();
    expect(await screen.findByText(/At least one policy is active/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'All suggested policies exist' })).toBeDisabled();
  });

  it('reports a failure and allows a retry', async () => {
    let fail = true;
    server.use(
      http.get('/api/admin/ai-usage/defaults', () =>
        fail ? apiError(500, 'server_error', 'Nope.') : HttpResponse.json(aiDefaults()),
      ),
    );
    const { user } = mount();
    expect(await screen.findByRole('alert')).toHaveTextContent('Nope.');
    fail = false;
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText(/Would be created/)).toBeInTheDocument();
  });
});
