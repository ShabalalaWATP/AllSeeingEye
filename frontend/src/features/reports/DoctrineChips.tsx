import { probabilityTerm } from '@/lib/doctrine';

import {
  confidenceTone,
  credibilityTone,
  flagLabel,
  flagTone,
  gradeTone,
  reliabilityTone,
  yardstickPosition,
  type Tone,
} from './doctrineTone';

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

/** An Admiralty grade, shown whole because the letter and number mean different things. */
export function GradeChip({ grade }: { grade: string }) {
  return <Chip label="Grade" value={grade} tone={gradeTone(grade)} />;
}

export function ReliabilityChip({
  reliability,
  credibility,
}: {
  reliability: string | null | undefined;
  credibility: number | null | undefined;
}) {
  return (
    <span className="flex flex-wrap gap-2">
      <Chip
        label="Reliability"
        value={reliability ?? 'Unknown'}
        tone={reliabilityTone(reliability)}
      />
      <Chip
        label="Credibility"
        value={credibility == null ? 'Unknown' : String(credibility)}
        tone={credibilityTone(credibility)}
      />
    </span>
  );
}

/** The flags recorded against a source, in their saved wording. */
export function SourceFlags({ flags }: { flags: readonly string[] }) {
  if (!flags.length) return null;
  return (
    <span className="flex flex-wrap gap-2">
      {flags.map((flag) => (
        <Chip key={flag} label="Source flag" value={flagLabel(flag)} tone={flagTone(flag)} />
      ))}
    </span>
  );
}
