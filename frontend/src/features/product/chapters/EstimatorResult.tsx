/**
 * The estimate itself: a low to high range per part and in total. The figures count
 * up when they change (static while the story is still); screen readers get the
 * settled range as one phrase. The summary can be handed to the enquiry form.
 */
import { useId } from 'react';

import { formatRange, wholeUnits, type Estimate, type Range } from '../content/costing';
import { CURRENCY_SYMBOLS, type Currency } from '../content/costModel';
import { useEnquiryPrefill } from '../enquiry/enquiryPrefill';
import { CountUp } from '../motion/CountUp';

function MoneyRange({ range, currency }: { range: Range; currency: Currency }) {
  const symbol = CURRENCY_SYMBOLS[currency];
  const low = wholeUnits(range.low);
  const high = wholeUnits(range.high);
  return (
    <>
      <span aria-hidden="true">
        {symbol}
        <CountUp value={low} />
        {low === high ? null : (
          <>
            {' to '}
            {symbol}
            <CountUp value={high} />
          </>
        )}
      </span>
      <span className="sr-only">{formatRange(range, currency)}</span>
    </>
  );
}

export interface EstimatorResultProps {
  result: Estimate;
  currency: Currency;
  invalid: boolean;
  summary: () => string;
}

export function EstimatorResult({ result, currency, invalid, summary }: EstimatorResultProps) {
  const prefill = useEnquiryPrefill();
  const noteId = useId();
  return (
    <>
      <div aria-live="polite">
        <p className="estimator-total">
          <span>Estimated monthly running cost</span>
          <strong data-testid="estimate-total">
            <MoneyRange range={result.total} currency={currency} />
          </strong>
        </p>
        <dl>
          <dt>AI usage ({result.runsPerMonth.toLocaleString('en-GB')} runs a month)</dt>
          <dd>
            <MoneyRange range={result.ai} currency={currency} />
          </dd>
          <dt>Server</dt>
          <dd>
            <MoneyRange range={result.hosting} currency={currency} />
          </dd>
          <dt>Licence and support</dt>
          <dd>Quoted on enquiry</dd>
        </dl>
      </div>
      {prefill.available ? (
        <div className="estimator-send">
          <button
            type="button"
            className="story-button story-button-small"
            disabled={invalid}
            aria-describedby={noteId}
            onClick={() => prefill.offer(summary())}
          >
            Send this estimate with an enquiry
          </button>
          <p id={noteId} className="estimator-hint">
            {invalid
              ? 'Correct the marked figures to send this estimate.'
              : 'Adds a summary to your enquiry message for you to edit. Nothing is sent until you send the enquiry.'}
          </p>
        </div>
      ) : null}
    </>
  );
}
