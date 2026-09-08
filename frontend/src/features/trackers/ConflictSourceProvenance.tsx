import type { LiveEvent } from '@/lib/api/eventSchemas';
import { isHttpUrl } from '@/lib/urls';

const fields = [
  ['original_publishers', 'Original publishers'],
  ['original_url', 'Original publication'],
  ['source_articles', 'Source articles'],
  ['source_original', 'Original source'],
] as const;
const MAX_TEXT = 800;
const MAX_LINK = 2_048;

/** Display the provider's attribution without treating multiple named outlets as independent. */
export function ConflictSourceProvenance({ event }: { event: LiveEvent }) {
  const attribution = fields.flatMap(([key, label]) => {
    const value = event.attributes[key];
    return typeof value === 'string' && value.trim() ? [{ key, label, value: value.trim() }] : [];
  });
  if (attribution.length === 0) return null;
  return (
    <section
      aria-label="Original source attribution"
      className="rounded-md border border-line/60 p-2 text-xs"
    >
      <dl className="space-y-2">
        {attribution.map(({ key, label, value }) => {
          const text = value.length > MAX_TEXT ? `${value.slice(0, MAX_TEXT)}… [truncated]` : value;
          const link =
            key !== 'original_publishers' && value.length <= MAX_LINK && isHttpUrl(value);
          return (
            <div key={key} className="break-words">
              <dt className="mb-0.5 font-medium text-muted">{label}</dt>
              <dd>
                {link ? (
                  <a
                    href={value}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-cyan hover:underline"
                  >
                    {text}
                  </a>
                ) : (
                  text
                )}
              </dd>
            </div>
          );
        })}
      </dl>
      <p className="mt-2 text-[11px] text-muted">
        Attribution supplied by the provider. Related sources may repeat the same account;
        independence is not established.
      </p>
    </section>
  );
}
