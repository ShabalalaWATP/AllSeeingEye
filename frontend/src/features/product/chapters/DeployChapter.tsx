/**
 * Chapter 9: Deploy. The deployment architecture draws itself as it passes through
 * the viewport (stroke offsets driven by --progress), followed by the cost estimator.
 * Until its figures are approved (KAN-178) the estimator appears only in development;
 * production builds say that costs are estimated with each organisation instead.
 */
import type { CSSProperties } from 'react';

import { COST_MODEL_STATUS } from '../content/costModel';
import { ARCHITECTURE } from '../content/platform';
import { Reveal } from '../motion/Reveal';
import { ScrollChapter } from '../motion/ScrollChapter';
import { CostEstimator } from './CostEstimator';

const SHOW_ESTIMATOR = COST_MODEL_STATUS === 'approved' || import.meta.env.DEV;

/**
 * Nodes follow the container view in docs/01_ARCHITECTURE.md: the browser, the four
 * Compose services inside the server boundary, and the external services the API may
 * call. ARCHITECTURE holds the services; the rest are named here.
 */
const DIAGRAM_NODES: readonly { id: string; name: string; detail: string }[] = [
  { id: 'browser', name: 'Browser', detail: 'Globe, research and reports' },
  ...ARCHITECTURE.filter((node) => node.id !== 'ai'),
  { id: 'sources', name: 'Public sources', detail: 'Feeds, APIs and catalogues' },
  ...ARCHITECTURE.filter((node) => node.id === 'ai'),
  { id: 'mail', name: 'Email service', detail: 'Optional, SMTP with TLS' },
];
const OUTSIDE_SERVER = new Set(['browser', 'sources', 'ai', 'mail']);

const NODES: Record<string, { x: number; y: number }> = {
  browser: { x: 120, y: 50 },
  caddy: { x: 120, y: 215 },
  api: { x: 360, y: 215 },
  db: { x: 600, y: 160 },
  parser: { x: 600, y: 270 },
  sources: { x: 120, y: 420 },
  ai: { x: 360, y: 420 },
  mail: { x: 600, y: 420 },
};
function at(id: string): { x: number; y: number } {
  return NODES[id] ?? { x: 0, y: 0 };
}

const LINKS: readonly [string, string][] = [
  ['browser', 'caddy'],
  ['caddy', 'api'],
  ['api', 'db'],
  ['api', 'parser'],
  ['api', 'sources'],
  ['api', 'ai'],
  ['api', 'mail'],
];

export function DeployChapter() {
  return (
    <ScrollChapter
      id="deploy"
      label="Deploy and cost"
      length={0.6}
      pin={false}
      className="story-deploy"
    >
      <div className="story-wrap">
        <p className="story-eyebrow">09 · Deploy</p>
        <h2 className="story-title">One server you run. Your database stays on it.</h2>
        <p className="story-lead">
          A Docker Compose stack on a single Linux server: Caddy at the edge, the API, PostgreSQL
          and an isolated document parser. Questions and selected evidence go to the AI provider you
          configure, links cited by saved reports go to the Internet Archive unless you turn that
          off, and email, push and webhooks are optional.
        </p>
        <figure className="architecture">
          <svg
            viewBox="0 0 720 470"
            role="img"
            aria-labelledby="architecture-title architecture-desc"
          >
            <title id="architecture-title">Deployment architecture</title>
            <desc id="architecture-desc">
              The browser reaches Caddy on your server, which serves the app and forwards API calls.
              Inside the Docker Compose boundary the API stores reports, evidence and accounts in
              PostgreSQL and sends supplied documents to an isolated parser with no network access.
              Outside it, the API collects from public sources, calls your chosen AI provider and,
              when configured, sends account email through an SMTP service.
            </desc>
            <g className="architecture-boundary">
              <rect x={10} y={115} width={700} height={215} rx={18} />
              <text x={28} y={140} className="architecture-detail">
                Your server · Docker Compose
              </text>
            </g>
            {LINKS.map(([from, to], index) => (
              <line
                key={`${from}-${to}`}
                className="architecture-link"
                x1={at(from).x}
                y1={at(from).y}
                x2={at(to).x}
                y2={at(to).y}
                pathLength={1}
                style={{ '--i': index } as CSSProperties}
              />
            ))}
            {DIAGRAM_NODES.map((node, index) => (
              <g
                key={node.id}
                className={
                  OUTSIDE_SERVER.has(node.id)
                    ? 'architecture-node architecture-node-external'
                    : 'architecture-node'
                }
                style={{ '--i': index } as CSSProperties}
              >
                <rect
                  x={at(node.id).x - 95}
                  y={at(node.id).y - 34}
                  width={190}
                  height={68}
                  rx={12}
                />
                <text
                  x={at(node.id).x}
                  y={at(node.id).y - 4}
                  textAnchor="middle"
                  className="architecture-name"
                >
                  {node.name}
                </text>
                <text
                  x={at(node.id).x}
                  y={at(node.id).y + 18}
                  textAnchor="middle"
                  className="architecture-detail"
                >
                  {node.detail}
                </text>
              </g>
            ))}
          </svg>
        </figure>
        <Reveal>
          <h3 className="story-subtitle">What would it cost to run?</h3>
          {SHOW_ESTIMATOR ? (
            <CostEstimator />
          ) : (
            <p className="story-lead">
              Running costs depend on your team size, research volume and AI provider. We will
              estimate them with you, including the server and model usage you can expect.
            </p>
          )}
        </Reveal>
      </div>
    </ScrollChapter>
  );
}
