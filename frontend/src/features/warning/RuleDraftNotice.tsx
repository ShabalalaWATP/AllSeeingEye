import { Link } from 'react-router';

import type { ReportWatchDraft } from '@/lib/alertRuleDraft';
import type { AreaWatchDraft } from '@/lib/areaWatchDraft';

const box = 'space-y-2 rounded border border-cyan/30 bg-cyan/5 p-3 text-sm';

export function reportVersionPath(source: ReportWatchDraft['source']): string {
  return `/reports/${encodeURIComponent(source.reportId)}?version=${String(source.version)}`;
}

/** A map area handed to the form: what it is and what still needs reviewing. */
export function AreaDraftNotice({
  draft,
  onDiscard,
}: {
  draft: AreaWatchDraft;
  onDiscard: () => void;
}) {
  return (
    <div className={box}>
      <h3 className="font-medium text-cyan">Watch this area</h3>
      <p>
        {draft.source === 'shape'
          ? 'Your exact research boundary is ready. Review categories and thresholds before adding an alert rule.'
          : draft.source === 'sketch-envelope'
            ? 'This approximate bounding rectangle includes areas outside your sketch. Adjust it before adding an alert rule.'
            : 'Your map bounds are ready to review. Adjust the location, categories and threshold before adding an alert rule.'}
      </p>
      <p className="text-xs text-muted">
        Nothing is saved yet. Reports are off by default. An alert rule counts published items in
        its time window and waits between alerts for its cooldown.
      </p>
      <button type="button" className="text-xs underline" onClick={onDiscard}>
        Discard map draft
      </button>
    </div>
  );
}

/** A judgement's "Watch for" indicators handed to the form, kept beside the keywords. */
export function ReportDraftNotice({
  draft,
  onDiscard,
}: {
  draft: ReportWatchDraft;
  onDiscard: () => void;
}) {
  const { source } = draft;
  return (
    <section aria-label="Draft from a report" className={box}>
      <h3 className="font-medium text-cyan">Watch for: draft from a report</h3>
      <p>
        From{' '}
        <Link to={reportVersionPath(source)} className="underline">
          “{source.title}”, version {source.version}
        </Link>
        , judgement {source.judgementNumber}: {source.statement}
      </p>
      <div>
        <p className="font-medium">Original indicator wording</p>
        <ul aria-label="Original indicator wording" className="mt-1 list-disc space-y-1 pl-5">
          {draft.indicators.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </div>
      <p className="text-xs leading-5 text-muted">
        Alert rules match keywords literally in item titles and summaries. They do not monitor the
        meaning of an indicator, so compare the keywords with the wording above and shorten each
        phrase to words you expect in a headline. A match is a prompt to check the evidence, not
        confirmation that the indicator has occurred.
      </p>
      {draft.areaNote && <p className="text-xs text-muted">{draft.areaNote}</p>}
      <p className="text-xs text-muted">
        Nothing is saved until you choose Add alert rule. Editing the draft never changes the saved
        report.
      </p>
      <button type="button" className="text-xs underline" onClick={onDiscard}>
        Discard draft
      </button>
    </section>
  );
}
