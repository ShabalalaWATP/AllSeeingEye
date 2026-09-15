/**
 * Development-only entry (registered when import.meta.env.DEV) for inspecting the
 * administration workspace without an account. It answers every /api request from
 * local fixtures, places an in-memory fixture administrator in the auth store and
 * then opens the real /admin routes, so the shell, guards and pages render as they
 * would for a verified administrator. No credential is used and nothing is saved.
 *
 * Query options: `to` (an /admin path), `scenario` (normal, empty or errors) and
 * `theme` (any appearance theme). Reload this page to change them.
 */
import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router';

import { LoadingScreen } from '@/components/ui/LoadingScreen';
import { useAuthStore } from '@/stores/auth';

import { installPreviewApi, PREVIEW_TOKEN, type PreviewScenario } from './adminPreviewFetch';
import { previewUsers } from './adminPreviewFixtures';

const SCENARIOS: readonly PreviewScenario[] = ['normal', 'empty', 'errors'];
const THEMES = [
  'obsidian',
  'slate',
  'light',
  'midnight',
  'aurora',
  'phosphor',
  'crimson',
  'graphite',
];

export default function AdminPreviewPage() {
  const [params] = useSearchParams();
  const status = useAuthStore((state) => state.status);
  const navigate = useNavigate();
  const requested = params.get('to') ?? '/admin';
  const to = /^\/admin(\/[a-z-]+)?$/.test(requested) ? requested : '/admin';
  const scenario = SCENARIOS.find((item) => item === params.get('scenario')) ?? 'normal';
  const theme = THEMES.find((item) => item === params.get('theme')) ?? 'obsidian';

  useEffect(() => {
    installPreviewApi(scenario, theme);
    // Wait for the app's own session bootstrap to settle so it cannot clear the fixture.
    if (status === 'unknown') return;
    const user = previewUsers[0];
    if (user === undefined) return;
    useAuthStore.setState({ status: 'authenticated', user, accessToken: PREVIEW_TOKEN });
    void navigate(to, { replace: true });
  }, [navigate, scenario, status, theme, to]);

  return <LoadingScreen label="Preparing administration preview" />;
}
