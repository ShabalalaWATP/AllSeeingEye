/**
 * axe checks on the signed-out pages (KAN-61). They render through the real route table, so
 * landmarks, heading order and names are checked as a reader meets them. See `src/test/axe.ts`
 * for the rules jsdom cannot evaluate.
 */
import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, it } from 'vitest';

import { expectNoAxeViolations } from '@/test/axe';
import { USER_PASSWORD, plainUser } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const PAGE = 30_000;

describe('signed-out pages have no axe violations', () => {
  it(
    'sign-in',
    async () => {
      renderApp('/login', 'anonymous');
      await screen.findByRole('heading', { level: 1, name: 'Sign in' });
      await expectNoAxeViolations();
    },
    PAGE,
  );

  it(
    'multi-factor verification',
    async () => {
      server.use(
        http.post('/api/auth/login', () =>
          HttpResponse.json({
            mfa_required: true,
            challenge_token: 'synthetic-login-challenge',
            expires_at: '2099-01-01T00:00:00Z',
            methods: ['authenticator', 'email'],
            enrollment_required: false,
            email_sent: false,
            authenticator_email_proof: false,
          }),
        ),
      );
      const { user } = renderApp('/login', 'anonymous');
      await user.type(await screen.findByLabelText('Email'), plainUser.email);
      await user.type(screen.getByLabelText('Password'), USER_PASSWORD);
      await user.click(screen.getByRole('button', { name: 'Sign in' }));
      await screen.findByRole('heading', { level: 1, name: /Verify your sign-in/ });
      await expectNoAxeViolations();
    },
    PAGE,
  );

  it(
    'administrator enrolment with an emailed confirmation code',
    async () => {
      const challenge = {
        mfa_required: true,
        challenge_token: 'synthetic-login-challenge',
        expires_at: '2099-01-01T00:00:00Z',
        methods: ['authenticator', 'email'],
        enrollment_required: true,
        email_sent: false,
        authenticator_email_proof: true,
      };
      server.use(
        http.post('/api/auth/login', () => HttpResponse.json(challenge)),
        http.post('/api/auth/mfa/email', () =>
          HttpResponse.json({ ...challenge, email_sent: true }),
        ),
      );
      const { user } = renderApp('/login', 'anonymous');
      await user.type(await screen.findByLabelText('Email'), plainUser.email);
      await user.type(screen.getByLabelText('Password'), USER_PASSWORD);
      await user.click(screen.getByRole('button', { name: 'Sign in' }));
      await screen.findByRole('heading', { level: 1, name: /Secure your account/ });
      await user.click(screen.getByRole('button', { name: 'Send email code' }));
      await screen.findByLabelText('Email confirmation code');
      await expectNoAxeViolations();
    },
    PAGE,
  );

  it(
    'account request',
    async () => {
      renderApp('/request-account', 'anonymous');
      await screen.findByRole('heading', { level: 1, name: 'Request an account' });
      await expectNoAxeViolations();
    },
    PAGE,
  );
});
