/**
 * What the product asset capture records (KAN-179). Every target is a development-only
 * preview page backed by synthetic fixtures; a target that tries to reach another
 * origin or an unanswered API route is skipped, never written.
 */

// Reserved for asset capture. Never accept a remote or operator-supplied base URL.
export const CAPTURE_PORT = 5183;
export const CAPTURE_ORIGIN = `http://127.0.0.1:${CAPTURE_PORT}`;

export interface CaptureTarget {
  /** File stem under public/product/ and the manifest id. */
  id: string;
  path: string;
  /** Alternative text for the image. */
  alt: string;
  viewport: { width: number; height: number };
  /** Shown before the image is ready to capture. */
  ready: string;
  /** Scrolled to the middle of the viewport before capture. */
  scrollTo?: string;
  /** Development-only preview controls to hide, by CSS selector or leading text. */
  hide?: string[];
  hideText?: string[];
  /** Synthetic answers for the few read-only API calls a preview makes ('GET /api/...'). */
  answers?: Record<string, unknown>;
}

const DESKTOP = { width: 1280, height: 800 };
// The report reader asks which report languages exist; two synthetic entries.
const LANGUAGES = {
  'GET /api/me/profile/languages': {
    version: '1',
    languages: [
      ['en', 'English', 'English', 'ltr'],
      ['ar', 'Arabic', 'العربية', 'rtl'],
    ].map(([code, label, native, direction]) => ({
      code,
      label,
      native_label: native,
      direction,
      report_supported: true,
      pdf_supported: true,
      detector_code: code,
      google_news_edition: null,
    })),
  },
};
const PHONE = { width: 390, height: 844 };
const PREVIEW_STATUS = 'nav[aria-label="Preview status"]';

export const CAPTURE_TARGETS: readonly CaptureTarget[] = [
  {
    id: 'globe-overview',
    path: '/dev/product-preview',
    alt: 'Illustrative dotted globe from the product page with its live layer list.',
    viewport: DESKTOP,
    ready: '#observe canvas',
    scrollTo: '#observe .observe-globe',
  },
  {
    id: 'report-reader',
    path: '/dev/report-preview#ready',
    alt: 'Illustrative report reader with a likelihood assessment, review status and exports.',
    viewport: DESKTOP,
    ready: 'main h1',
    answers: LANGUAGES,
    hide: [PREVIEW_STATUS],
  },
  {
    id: 'report-evidence',
    path: '/dev/report-preview#annex',
    alt: 'Illustrative evidence annex with graded sources behind a report.',
    viewport: DESKTOP,
    ready: 'main',
    answers: LANGUAGES,
    hide: [PREVIEW_STATUS],
  },
  {
    id: 'report-mobile',
    path: '/dev/report-preview#ready',
    alt: 'Illustrative report reader on a phone-sized screen.',
    viewport: PHONE,
    ready: 'main h1',
    answers: LANGUAGES,
    hide: [PREVIEW_STATUS],
  },
  {
    id: 'photo-geolocation',
    path: '/dev/pages-preview#geolocation',
    alt: 'Illustrative photo geolocation workspace before an image is supplied.',
    viewport: DESKTOP,
    ready: 'main h1',
    answers: { 'GET /api/teams': { items: [] } },
  },
  {
    id: 'sources',
    path: '/dev/pages-preview#sources',
    alt: 'Illustrative sources and connections directory with connection states.',
    viewport: DESKTOP,
    ready: 'main h1',
  },
  {
    id: 'map-guide',
    path: '/dev/navigation-preview',
    alt: 'Illustrative navigation rail, layer controls and map guide.',
    viewport: DESKTOP,
    ready: 'main',
    hideText: ['Open the search palette'],
  },
  {
    id: 'economy',
    path: '/dev/economy-preview#ready',
    alt: 'Illustrative economy workspace with plain English explainers.',
    viewport: DESKTOP,
    ready: 'main h1',
    hideText: ['Fixture preview'],
  },
  {
    id: 'admin-ai',
    path: '/dev/admin-preview?to=/admin/llm',
    alt: 'Illustrative administration page for AI connections, with keys hidden.',
    viewport: DESKTOP,
    ready: 'main h1',
  },
];

/** Not captured, with the reason, so the asset list stays honest. */
export const NOT_CAPTURED: readonly { asset: string; reason: string }[] = [
  {
    asset: 'Research composer',
    reason:
      'No development preview renders it from fixtures; it needs a signed-in session, ' +
      'which only the production-build regression lane provides on its own port.',
  },
  {
    asset: 'Subscriptions and editions',
    reason:
      'Its preview loads usage, teams, templates, plans and countries from the API, so ' +
      'without a backend it shows error states instead of editions.',
  },
  {
    asset: 'Cyber workspace',
    reason:
      'Its preview requests attack trends from a licence-restricted source through the ' +
      'API; that panel must not appear in promotional images.',
  },
  {
    asset: 'Alerts on mobile',
    reason: 'No development preview renders the alerts workspace from fixtures.',
  },
  {
    asset: 'Public figures tracker',
    reason:
      'Its preview shows portraits of real people from the packaged roster, which are ' +
      'real personal data and not cleared for promotional use.',
  },
  {
    asset: 'Ukraine war tracker',
    reason:
      'Its preview shows third-party photographs, including a real person, whose licences ' +
      'need review before any promotional use.',
  },
  {
    asset: 'Layer close-ups on the real globe',
    reason:
      'The real globe needs third-party map tiles; the product page globe overview is ' +
      'the synthetic substitute.',
  },
  {
    asset: 'Motion loops (WebM and MP4)',
    reason:
      'Playwright records only untrimmed VP8 WebM and no encoder (ffmpeg) is installed, ' +
      'so VP9 or AV1 loops with an MP4 fallback cannot be produced reliably.',
  },
];
