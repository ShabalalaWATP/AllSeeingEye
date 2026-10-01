/**
 * Allowance figures read the same in every browser: UK number grouping and the app's
 * date format, never whatever locale the browser happens to report.
 */
import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { useProfileStore } from '@/stores/profile';
import { aiOverride, aiSummary, aiTotals } from '@/test/fixtures.aiUsage';
import { plainUser } from '@/test/fixtures';
import { defaultProfile } from '@/test/handlers.profile';
import { applySession } from '@/test/render';

import { AllowanceCard, ObservedTotals, UsageBar } from './AllowanceCards';

/** Pretend the browser reports German, so any locale-default formatting shows up. */
beforeEach(() => {
  vi.spyOn(Number.prototype, 'toLocaleString').mockImplementation(function (
    this: number,
    locales?: Intl.LocalesArgument,
    options?: Intl.NumberFormatOptions,
  ) {
    return new Intl.NumberFormat(locales ?? 'de-DE', options).format(this);
  });
  vi.spyOn(Date.prototype, 'toLocaleString').mockImplementation(function (
    this: Date,
    locales?: Intl.LocalesArgument,
    options?: Intl.DateTimeFormatOptions,
  ) {
    return new Intl.DateTimeFormat(
      locales ?? 'de-DE',
      options ?? { dateStyle: 'short', timeStyle: 'medium' },
    ).format(this);
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  useProfileStore.setState({ owner: null, profile: null });
});

const item = aiSummary({
  used_requests: 1200,
  reserved_requests: 34,
  used_tokens: 1_234_000,
  reserved_tokens: 567,
  request_limit: 5000,
  token_limit: 2_000_000,
  period_end: '2026-10-01T12:00:00Z',
  override: aiOverride({ expires_at: '2026-09-08T06:30:00Z' }),
});

describe('allowance cards in a non-UK browser', () => {
  it('formats counts with UK grouping and dates in UTC by default', () => {
    render(<AllowanceCard item={item} />);
    expect(screen.getByText('1,234 / 5,000')).toBeInTheDocument();
    expect(screen.getByText('1,234,567 / 2,000,000')).toBeInTheDocument();
    expect(screen.getByText('Resets 01/10/2026, 12:00 UTC')).toBeInTheDocument();
    expect(screen.getByText('Temporary override until 08/09/2026, 06:30 UTC')).toBeInTheDocument();
  });

  it("follows the signed-in account's time zone and date format", () => {
    applySession('user');
    useProfileStore.setState({
      owner: plainUser.id,
      profile: { ...defaultProfile, timezone: 'Europe/London', date_format: 'iso' },
    });
    render(<AllowanceCard item={item} />);
    expect(screen.getByText('Resets 2026-10-01 13:00 Europe/London')).toBeInTheDocument();
    useAuthStore.getState().clearSession();
  });

  it('ignores a profile loaded for a different account', () => {
    applySession('admin');
    useProfileStore.setState({
      owner: plainUser.id,
      profile: { ...defaultProfile, timezone: 'Asia/Tokyo' },
    });
    render(<AllowanceCard item={item} />);
    expect(screen.getByText('Resets 01/10/2026, 12:00 UTC')).toBeInTheDocument();
  });

  it('formats usage bars and observed totals with UK grouping', () => {
    render(
      <>
        <UsageBar label="Requests" used={12345} limit={null} />
        <ObservedTotals
          label="Your usage"
          totals={aiTotals({
            used_requests: 4321,
            used_tokens: 1_000_000,
            used_input_tokens: 600_000,
            used_output_tokens: 400_000,
            unknown_requests: 1500,
          })}
        />
      </>,
    );
    expect(screen.getByText('12,345 used')).toBeInTheDocument();
    expect(screen.getByText(/4,321 requests, 1,000,000\s+tokens this month/)).toBeInTheDocument();
    expect(screen.getByText(/600,000 in,\s+400,000 out/)).toBeInTheDocument();
    expect(screen.getByText(/1,500 with unconfirmed usage/)).toBeInTheDocument();
  });
});
