/**
 * Captures the product page's illustrative assets and Open Graph image (KAN-179) from
 * development preview pages and their synthetic fixtures. Each image is written as
 * WebP (encoded in the page with canvas.toBlob) with a PNG fallback, and the typed
 * manifest records the sizes. Images are staged first: public/product and the manifest
 * change only once every target is captured, so a failed or skipped target never drops
 * a committed asset. Run through `pnpm capture:assets`; see docs/images/README.md.
 */
import { spawnSync } from 'node:child_process';
import {
  appendFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import { dirname, resolve } from 'node:path';

import { expect, test, type Page } from '@playwright/test';

import { BRAND_GROUND } from '../src/components/brand/tokens';
import { PAGE_DESCRIPTION, PAGE_TITLE } from '../src/features/product/content/chapters';
import {
  CAPTURE_ORIGIN,
  CAPTURE_TARGETS,
  NOT_CAPTURED,
  type CaptureTarget,
} from './captureTargets';
import { CAPTURE_PATHS } from './capturePaths';
import { missingCaptures, promoteCaptures, stagedImage, STAGING_DIR } from './captureStaging';

const { frontend: FRONTEND, productDir: PRODUCT_DIR, skippedLog: SKIPPED_LOG } = CAPTURE_PATHS;
const OG_FILE = resolve(FRONTEND, 'public/brand/og-enterprise.png');
const MANIFEST = resolve(FRONTEND, 'src/features/product/content/assets.ts');
const REPORT = resolve(FRONTEND, '../output/playwright/capture-report.json');
const WEBP_QUALITY = 0.82;

// Bootstrap calls every page makes; answered as a signed-out installation.
const BOOTSTRAP: Record<string, { status: number; json: unknown }> = {
  'POST /api/auth/refresh': {
    status: 401,
    json: { error: { code: 'unauthenticated', message: 'No session during capture.' } },
  },
  'GET /api/site': {
    status: 200,
    json: { product_page_enabled: false, enterprise_enquiries_enabled: false },
  },
};

/** Aborts every other origin and answers API calls locally; returns what was refused. */
async function guard(page: Page, answers: Record<string, unknown> = {}) {
  const refused: string[] = [];
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== CAPTURE_ORIGIN) {
      refused.push(`External request: ${url.origin}${url.pathname}`);
      await route.abort('blockedbyclient');
      return;
    }
    if (!url.pathname.startsWith('/api/')) {
      await route.continue();
      return;
    }
    const key = `${request.method()} ${url.pathname}`;
    const known = Object.hasOwn(answers, key)
      ? { status: 200, json: answers[key] }
      : BOOTSTRAP[key];
    if (known === undefined) refused.push(`Unanswered API call: ${key}`);
    await route.fulfill(
      known ?? { status: 503, json: { error: { code: 'capture', message: 'No backend.' } } },
    );
  });
  return refused;
}

async function settle(page: Page, target: Pick<CaptureTarget, 'ready' | 'scrollTo'>) {
  await page.locator(target.ready).first().waitFor({ state: 'visible' });
  // No focus rings or tooltips from the page's initial focus or the pointer.
  await page.mouse.move(0, 0);
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
  });
  if (target.scrollTo !== undefined) {
    await page.locator(target.scrollTo).evaluate((element) => {
      element.scrollIntoView({ block: 'center' });
    });
  }
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
  await page.waitForTimeout(1200);
}

/** Re-encodes a PNG in the page, so no image tool is needed on the machine. */
async function encode(page: Page, png: Buffer, type: 'image/webp' | 'image/png') {
  const base64 = await page.evaluate(
    async ({ data, type, quality }) => {
      const image = new Image();
      image.src = `data:image/png;base64,${data}`;
      await image.decode();
      const canvas = document.createElement('canvas');
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      canvas.getContext('2d')?.drawImage(image, 0, 0);
      const blob = await new Promise<Blob | null>((done) => {
        canvas.toBlob(done, type, quality);
      });
      if (blob?.type !== type) throw new Error(`This browser cannot encode ${type}.`);
      const bytes = new Uint8Array(await blob.arrayBuffer());
      let binary = '';
      for (const byte of bytes) binary += String.fromCharCode(byte);
      return btoa(binary);
    },
    { data: png.toString('base64'), type, quality: WEBP_QUALITY },
  );
  return Buffer.from(base64, 'base64');
}

function size(png: Buffer) {
  return { width: png.readUInt32BE(16), height: png.readUInt32BE(20) };
}

for (const target of CAPTURE_TARGETS) {
  test(`captures ${target.id}`, async ({ page }) => {
    const refused = await guard(page, target.answers);
    await page.setViewportSize(target.viewport);
    await page.goto(target.path);
    await settle(page, target);
    if (refused.length > 0) {
      const reason = [...new Set(refused)].join('; ');
      appendFileSync(SKIPPED_LOG, `${JSON.stringify({ id: target.id, reason })}\n`);
      test.skip(true, `Not captured without the network: ${reason}`);
      return;
    }
    await page.evaluate(
      ({ selectors, prefixes }) => {
        const hidden = selectors.length === 0 ? [] : document.querySelectorAll(selectors.join(','));
        hidden.forEach((element) => {
          if (element instanceof HTMLElement) element.style.display = 'none';
        });
        document.querySelectorAll<HTMLElement>('main p, main button').forEach((element) => {
          const text = element.textContent.trim();
          if (prefixes.some((prefix) => text.startsWith(prefix))) element.style.display = 'none';
        });
      },
      { selectors: target.hide ?? [], prefixes: target.hideText ?? [] },
    );
    const png = await page.screenshot({ animations: 'disabled', caret: 'hide' });
    const webp = await encode(page, png, 'image/webp');
    writeFileSync(stagedImage(STAGING_DIR, target.id, 'png'), png);
    writeFileSync(stagedImage(STAGING_DIR, target.id, 'webp'), webp);
  });
}

test('composes the Open Graph image from the real brand mark', async ({ page }) => {
  const refused = await guard(page);
  await page.setViewportSize({ width: 900, height: 700 });
  await page.goto('/brand/capture');
  await settle(page, { ready: '[data-testid="brand-capture"] canvas' });
  expect(refused).toEqual([]);
  const eye = await page.getByTestId('brand-capture').screenshot({ animations: 'allow' });
  const [title = PAGE_TITLE, eyebrow = ''] = PAGE_TITLE.split(' · ');
  const og = await page.evaluate(
    async ({ eye, ground, title, eyebrow, lead }) => {
      await Promise.all([
        document.fonts.load('600 64px "Inter Variable"'),
        document.fonts.load('400 26px "Inter Variable"'),
        document.fonts.load('600 18px "JetBrains Mono"'),
      ]);
      const canvas = document.createElement('canvas');
      canvas.width = 1200;
      canvas.height = 630;
      const context = canvas.getContext('2d');
      if (context === null) throw new Error('No 2D canvas.');
      context.fillStyle = ground;
      context.fillRect(0, 0, 1200, 630);
      const glow = context.createRadialGradient(270, 315, 0, 270, 315, 360);
      glow.addColorStop(0, 'rgba(255, 111, 55, 0.16)');
      glow.addColorStop(1, 'rgba(255, 111, 55, 0)');
      context.fillStyle = glow;
      context.fillRect(0, 0, 1200, 630);
      const image = new Image();
      image.src = `data:image/png;base64,${eye}`;
      await image.decode();
      // Fade the capture's square edges, then 'lighten' keeps the glow behind the mark.
      const mark = document.createElement('canvas');
      mark.width = 420;
      mark.height = 420;
      const markContext = mark.getContext('2d');
      if (markContext === null) throw new Error('No 2D canvas.');
      markContext.drawImage(image, 0, 0, 420, 420);
      const fade = markContext.createRadialGradient(210, 210, 120, 210, 210, 210);
      fade.addColorStop(0, 'rgba(0, 0, 0, 1)');
      fade.addColorStop(1, 'rgba(0, 0, 0, 0)');
      markContext.globalCompositeOperation = 'destination-in';
      markContext.fillStyle = fade;
      markContext.fillRect(0, 0, 420, 420);
      context.globalCompositeOperation = 'lighten';
      context.drawImage(mark, 40, 105);
      context.globalCompositeOperation = 'source-over';
      const left = 500;
      const width = 650;
      context.fillStyle = '#ff6f37';
      context.font = '600 18px "JetBrains Mono"';
      context.letterSpacing = '3px';
      context.fillText(eyebrow.toUpperCase(), left, 215);
      context.letterSpacing = '0px';
      let headline = 64;
      do {
        context.font = `600 ${headline}px "Inter Variable"`;
        headline -= 2;
      } while (context.measureText(`${title}.`).width > width && headline > 40);
      context.fillStyle = '#ece7df';
      context.fillText(title, left, 300);
      context.fillStyle = '#ff6f37';
      context.fillText('.', left + context.measureText(title).width, 300);
      context.fillStyle = '#a29daa';
      context.font = '400 26px "Inter Variable"';
      const lines: string[] = [''];
      for (const word of lead.split(' ')) {
        const line = lines[lines.length - 1] ?? '';
        const next = line === '' ? word : `${line} ${word}`;
        if (context.measureText(next).width > width) lines.push(word);
        else lines[lines.length - 1] = next;
      }
      lines.forEach((line, index) => {
        context.fillText(line, left, 360 + index * 38);
      });
      const blob = await new Promise<Blob | null>((done) => {
        canvas.toBlob(done, 'image/png');
      });
      if (blob === null) throw new Error('Could not encode the Open Graph image.');
      const bytes = new Uint8Array(await blob.arrayBuffer());
      let binary = '';
      for (const byte of bytes) binary += String.fromCharCode(byte);
      return btoa(binary);
    },
    { eye: eye.toString('base64'), ground: BRAND_GROUND, title, eyebrow, lead: PAGE_DESCRIPTION },
  );
  const png = Buffer.from(og, 'base64');
  expect(size(png)).toEqual({ width: 1200, height: 630 });
  writeFileSync(OG_FILE, png);
});

function quote(text: string): string {
  return `'${text.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;
}

/** This run's captures, read from staging: the global setup emptied it. */
function capturedAssets() {
  return CAPTURE_TARGETS.flatMap((target) => {
    const png = stagedImage(STAGING_DIR, target.id, 'png');
    const webp = stagedImage(STAGING_DIR, target.id, 'webp');
    if (!existsSync(png) || !existsSync(webp)) return [];
    const bytes = statSync(png).size + statSync(webp).size;
    return [{ id: target.id, alt: target.alt, ...size(readFileSync(png)), bytes }];
  });
}

function writeManifest(captured: ReturnType<typeof capturedAssets>): void {
  const entries = captured
    .map((asset) =>
      [
        '  {',
        `    id: ${quote(asset.id)},`,
        `    alt: ${quote(asset.alt)},`,
        `    width: ${asset.width},`,
        `    height: ${asset.height},`,
        `    webp: ${quote(`/product/${asset.id}.webp`)},`,
        `    png: ${quote(`/product/${asset.id}.png`)},`,
        '  },',
      ].join('\n'),
    )
    .join('\n');
  writeFileSync(
    MANIFEST,
    [
      '/**',
      ' * Generated by `pnpm capture:assets` (frontend/browser/assets.capture.ts); do not edit',
      ' * by hand. Every image is captured from a development preview with synthetic fixtures',
      ' * and must be captioned "Illustrative" wherever it is shown.',
      ' */',
      '',
      'export interface ProductAsset {',
      '  id: string;',
      '  alt: string;',
      '  /** Intrinsic size in CSS pixels, for width and height attributes and srcset. */',
      '  width: number;',
      '  height: number;',
      '  webp: string;',
      '  /** Fallback for browsers without WebP. */',
      '  png: string;',
      '}',
      '',
      `export const PRODUCT_ASSETS: readonly ProductAsset[] = [\n${entries}\n];`,
      '',
      'export const OPEN_GRAPH_IMAGE = {',
      "  url: '/brand/og-enterprise.png',",
      '  width: 1200,',
      '  height: 630,',
      "  alt: 'The All Seeing Eye brand mark, a glowing eye, beside the name and a short description.',",
      '} as const;',
      '',
    ].join('\n'),
  );
  // Keep the generated module in the repository's formatting.
  spawnSync('pnpm', ['exec', 'prettier', '--write', MANIFEST], { cwd: FRONTEND, shell: true });
}

// Runs again after a worker restart; only a pass that finds every target staged
// replaces the committed images and rewrites the manifest.
test.afterAll(() => {
  const ids = CAPTURE_TARGETS.map((target) => target.id);
  const captured = capturedAssets();
  const missing = missingCaptures(STAGING_DIR, ids);
  const skipped = existsSync(SKIPPED_LOG)
    ? readFileSync(SKIPPED_LOG, 'utf8')
        .split('\n')
        .filter(Boolean)
        .map((line) => JSON.parse(line) as unknown)
    : [];
  const complete = missing.length === 0;
  if (complete) {
    promoteCaptures(STAGING_DIR, PRODUCT_DIR, ids);
    writeManifest(captured);
  }
  mkdirSync(dirname(REPORT), { recursive: true });
  const report = { complete, captured, missing, skipped, notCaptured: NOT_CAPTURED };
  writeFileSync(REPORT, `${JSON.stringify(report, null, 2)}\n`);
  if (!complete) {
    throw new Error(
      `Not captured: ${missing.join(', ')}. public/product and the manifest are unchanged; ` +
        'fix the target, or move it to NOT_CAPTURED, and run the whole capture again.',
    );
  }
});
