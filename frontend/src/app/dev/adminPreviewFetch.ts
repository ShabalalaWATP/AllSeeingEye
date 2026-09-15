/**
 * Development-only in-browser API stand-in for /dev/admin-preview. Every /api
 * request is answered locally, so the preview never reaches a backend or sends a
 * cookie. Writes are refused so no control pretends a change succeeded.
 */
import {
  defaultProfileForPreview,
  previewAudit,
  previewConnections,
  previewFirms,
  previewPolicy,
  previewProfiles,
  previewRequests,
  previewSources,
  previewTeam,
  previewUsage,
  previewUsers,
} from './adminPreviewFixtures';

export type PreviewScenario = 'normal' | 'empty' | 'errors';
export const PREVIEW_TOKEN = 'admin-preview-token';

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const failure = (status: number, code: string, message: string) =>
  json({ error: { code, message } }, status);

type Handler = (url: URL) => Response;

function routes(scenario: PreviewScenario, theme: string): [RegExp, Handler][] {
  const empty = scenario === 'empty';
  const broken = scenario === 'errors';
  return [
    [/^\/api\/me$/, () => json(previewUsers[0])],
    [/^\/api\/me\/profile$/, () => json({ ...defaultProfileForPreview, appearance_theme: theme })],
    [
      /^\/api\/auth\/mfa$/,
      () =>
        json({
          methods: empty ? [] : ['authenticator'],
          available_methods: ['authenticator', 'email'],
          required: true,
        }),
    ],
    [/^\/api\/auth\/totp$/, () => json({ enabled: !empty, available: true })],
    [/^\/api\/admin\/account-requests$/, () => json({ items: empty ? [] : previewRequests })],
    [
      /^\/api\/admin\/users$/,
      () => json({ items: empty ? previewUsers.slice(0, 1) : previewUsers }),
    ],
    [/^\/api\/teams$/, () => json({ items: empty ? [] : [previewTeam.team] })],
    [/^\/api\/teams\/[^/]+$/, () => json(previewTeam)],
    [/^\/api\/me\/team-invitations$/, () => json({ items: [] })],
    [/^\/api\/teams\/[^/]+\/invitations$/, () => json({ items: [] })],
    [
      /^\/api\/admin\/audit-log$/,
      (url) => {
        if (broken) return failure(403, 'forbidden', 'Administrator verification required.');
        if (empty) return json({ items: [], next_before: null });
        const before = Number(url.searchParams.get('before') ?? Infinity);
        const items = previewAudit.filter((entry) => entry.id < before).slice(0, 20);
        const last = items.at(-1);
        return json({
          items,
          next_before:
            last !== undefined && last.id > (previewAudit.at(-1)?.id ?? 0) ? last.id : null,
        });
      },
    ],
    [
      /^\/api\/admin\/sources$/,
      () =>
        broken
          ? failure(503, 'unavailable', 'The collector registry did not respond.')
          : json({ items: empty ? [] : previewSources }),
    ],
    [/^\/api\/admin\/sources\/[^/]+\/connection$/, () => json(previewFirms)],
    [
      /^\/api\/admin\/llm\/profiles$/,
      () => json({ items: empty ? [] : previewProfiles, encryption_available: !empty }),
    ],
    [/^\/api\/admin\/llm\/connections$/, () => json({ items: empty ? [] : previewConnections })],
    [/^\/api\/admin\/ai-usage\/policies$/, () => json(empty ? [] : [previewPolicy])],
    [
      /^\/api\/admin\/ai-usage\/preview$/,
      () =>
        broken
          ? failure(500, 'unexpected_error', 'Usage totals are temporarily unavailable.')
          : json(empty ? { ...previewUsage(), items: [], unknown_calls: 0 } : previewUsage()),
    ],
  ];
}

let installed: typeof window.fetch | null = null;

export function installPreviewApi(scenario: PreviewScenario, theme: string) {
  const original = installed ?? window.fetch.bind(window);
  installed = original;
  const table = routes(scenario, theme);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(
      input instanceof Request ? input.url : String(input),
      window.location.origin,
    );
    if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/')) {
      return original(input, init);
    }
    const method = (
      init?.method ?? (input instanceof Request ? input.method : 'GET')
    ).toUpperCase();
    if (method !== 'GET') {
      return Promise.resolve(
        failure(403, 'preview_read_only', 'The design preview does not save changes.'),
      );
    }
    const match = table.find(([pattern]) => pattern.test(url.pathname));
    return Promise.resolve(
      match ? match[1](url) : failure(404, 'not_found', 'Not part of the preview.'),
    );
  };
}
