import type { SourceAsset } from '@/lib/api/sourceContext';
import { ConnectionBadge } from './ConnectionBadge';

const DELIVERY_LABELS: Record<SourceAsset['delivery'], string> = {
  official_index: 'Official index',
  curated_catalogue: 'Curated catalogue',
  third_party_directory: 'Third-party directory',
  bundled_snapshot: 'Packaged snapshot',
  request_service: 'Queried on request',
  browser_direct: 'Loaded by your browser',
};

/** A camera index, map layer or dataset; every value renders as text, never as HTML. */
export function SourceAssetRow({ asset }: { asset: SourceAsset }) {
  const requirement = asset.requirement;
  const facts = [
    asset.as_of ? `As of ${asset.as_of}` : null,
    asset.records !== null ? `${asset.records.toLocaleString('en-GB')} records` : null,
    asset.refresh_note,
  ].filter(Boolean);
  return (
    <li className="min-w-0 py-5 [overflow-wrap:anywhere]">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h4 className="text-base font-semibold text-text">{asset.name}</h4>
          <p className="mt-1 text-sm text-muted">{asset.organisation}</p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2 text-xs text-muted">
          <ConnectionBadge state={asset.state} optional={requirement?.optional ?? false} />
          <span>{DELIVERY_LABELS[asset.delivery]}</span>
        </div>
      </div>
      <p className="mt-3 text-sm text-text/85">{asset.description}</p>
      <p className="mt-1 text-xs text-muted">{asset.coverage_note}</p>
      <p className="mt-2 text-xs leading-5 text-muted">{asset.detail}</p>
      {requirement && requirement.note !== asset.detail && (
        <p
          className={`mt-2 text-xs leading-5 ${requirement.satisfied === false && !requirement.optional ? 'text-amber' : 'text-muted'}`}
        >
          {requirement.note}
          {requirement.setting && (
            <span className="ml-2 font-mono text-[10px] text-muted">{requirement.setting}</span>
          )}
        </p>
      )}
      <details className="text-xs text-muted">
        <summary className="w-fit cursor-pointer py-2 focus-visible:outline-2 focus-visible:outline-ember">
          Licence and provenance
        </summary>
        <p className="py-2 leading-relaxed">{asset.licence_note}</p>
        <p className="leading-relaxed">{facts.join(' · ')}</p>
        <p className="mt-1 flex flex-wrap gap-x-3 font-mono">
          <span>{asset.id}</span>
          {asset.homepage && (
            <a
              href={asset.homepage}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-ember"
            >
              Publisher website
            </a>
          )}
        </p>
      </details>
    </li>
  );
}
