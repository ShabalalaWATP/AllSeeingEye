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

const NODES: Record<string, { x: number; y: number }> = {
  caddy: { x: 120, y: 120 },
  api: { x: 360, y: 120 },
  db: { x: 600, y: 60 },
  parser: { x: 600, y: 180 },
  ai: { x: 360, y: 280 },
};
function at(id: string): { x: number; y: number } {
  return NODES[id] ?? { x: 0, y: 0 };
}

const LINKS: readonly [string, string][] = [
  ['caddy', 'api'],
  ['api', 'db'],
  ['api', 'parser'],
  ['api', 'ai'],
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
        <h2 className="story-title">One server. One command. Your data stays put.</h2>
        <p className="story-lead">
          A Docker Compose stack on a single Linux server: Caddy at the edge, the API, PostgreSQL
          and an isolated document parser. Model calls go only to the provider you configure.
        </p>
        <figure className="architecture">
          <svg
            viewBox="0 0 720 340"
            role="img"
            aria-labelledby="architecture-title architecture-desc"
          >
            <title id="architecture-title">Deployment architecture</title>
            <desc id="architecture-desc">
              Browsers reach Caddy, which serves the app and forwards API calls. The API stores
              reports, evidence and accounts in PostgreSQL, sends documents to an isolated parser
              with no network access, and calls your chosen AI provider.
            </desc>
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
            {ARCHITECTURE.map((node, index) => (
              <g
                key={node.id}
                className="architecture-node"
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
