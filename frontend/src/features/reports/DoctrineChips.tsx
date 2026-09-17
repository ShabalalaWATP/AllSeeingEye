import { probabilityTerm } from '@/lib/doctrine';

import { confidenceTone, yardstickPosition, type Tone } from './doctrineTone';

/**
 * Labelled chips for recorded doctrine values. Every chip shows its label and its
 * value as text; the tone only repeats what the words already say.
 */
export function Chip({
  label,
  value,
  tone = 'neutral',
  children,
}: {
  label: string;
  value: string;
  tone?: Tone;
  children?: React.ReactNode;
}) {
  return (
    <span className="report-reader-fact" data-tone={tone}>
      <span className="report-reader-fact-label">{label}</span>
      <span>{value}</span>
      {children}
    </span>
  );
}

/** The UK PHIA yardstick term, with its band position on the seven-band scale. */
export function LikelihoodChip({ probability }: { probability: string }) {
  const { band, bands } = yardstickPosition(probability);
  return (
    <Chip label="Likelihood" value={probabilityTerm(probability)} tone="neutral">
      {band > 0 && (
        <span className="report-reader-scale" aria-hidden="true">
          {Array.from({ length: bands }, (_, index) => (
            <span key={index} data-filled={index < band} />
          ))}
        </span>
      )}
    </Chip>
  );
}

export function ConfidenceChip({ confidence }: { confidence: string }) {
  return <Chip label="Confidence" value={confidence} tone={confidenceTone(confidence)} />;
}
