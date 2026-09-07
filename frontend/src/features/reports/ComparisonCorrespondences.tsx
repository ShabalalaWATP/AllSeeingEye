import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField } from '@/components/ui/Field';
import type { AnnotationComparisonInput } from '@/lib/api/annotationComparisons';
import type { Report } from '@/lib/api/reports';
import {
  annotationKind,
  annotationKey,
  annotationRoot,
  annotationTitle,
} from './comparisonSelection';
import type { ComparisonAnnotation } from './comparisonSelection';
interface Option {
  value: string;
  label: string;
  kind?: string;
}
function PairForm({
  title,
  before,
  after,
  onAdd,
}: {
  title: string;
  before: Option[];
  after: Option[];
  onAdd: (left: string, right: string, rationale: string) => void;
}) {
  const [left, setLeft] = useState('');
  const [right, setRight] = useState('');
  const [reason, setReason] = useState('');
  const selected = before.find((item) => item.value === left);
  const targets = after.filter((item) => !selected?.kind || item.kind === selected.kind);
  return (
    <fieldset className="space-y-3 border border-line p-3">
      <legend className="text-sm">{title}</legend>
      <p className="text-xs text-muted">
        Declare a correspondence only when you intend these exact inputs to be compared. This
        records your judgement, not verified identity or semantic sameness.
      </p>
      <SelectField
        label={`${title}: selected before`}
        value={left}
        options={[{ value: '', label: 'Choose input' }, ...before]}
        onChange={(event) => {
          setLeft(event.target.value);
          setRight('');
        }}
      />
      <SelectField
        label={`${title}: selected after`}
        value={right}
        options={[{ value: '', label: 'Choose input' }, ...targets]}
        onChange={(event) => setRight(event.target.value)}
      />
      <TextAreaField
        label={`${title}: rationale`}
        value={reason}
        maxLength={500}
        onChange={(event) => setReason(event.target.value)}
      />
      <Button
        variant="secondary"
        disabled={!selected || !targets.some((item) => item.value === right) || !reason.trim()}
        onClick={() => {
          onAdd(left, right, reason);
          setLeft('');
          setRight('');
          setReason('');
        }}
      >
        Add {title.toLowerCase()}
      </Button>
    </fieldset>
  );
}
export function ComparisonCorrespondences({
  before,
  after,
  beforeReport,
  afterReport,
  annotations,
  judgements,
  onAnnotations,
  onJudgements,
}: {
  before: ComparisonAnnotation[];
  after: ComparisonAnnotation[];
  beforeReport: Report;
  afterReport: Report;
  annotations: NonNullable<AnnotationComparisonInput['correspondences']>;
  judgements: NonNullable<AnnotationComparisonInput['judgement_correspondences']>;
  onAnnotations: (value: NonNullable<AnnotationComparisonInput['correspondences']>) => void;
  onJudgements: (
    value: NonNullable<AnnotationComparisonInput['judgement_correspondences']>,
  ) => void;
}) {
  const sameRoot = (a: ComparisonAnnotation, b: ComparisonAnnotation) =>
    annotationKind(a) === annotationKind(b) && annotationRoot(a) === annotationRoot(b);
  const options = (items: ComparisonAnnotation[]) =>
    items.map((value) => ({
      value: annotationKey(value),
      kind: annotationKind(value),
      label: `${annotationTitle(value)} / revision ${value.number} / ${value.id}`,
    }));
  const left = options(
    before.filter(
      (value) =>
        !after.some((other) => sameRoot(value, other)) &&
        !annotations.some((pair) => pair.before_revision_id === value.id),
    ),
  );
  const right = options(
    after.filter(
      (value) =>
        !before.some((other) => sameRoot(value, other)) &&
        !annotations.some((pair) => pair.after_revision_id === value.id),
    ),
  );
  return (
    <details className="space-y-3 rounded border border-line p-4">
      <summary className="cursor-pointer font-medium">
        Optional operator-declared correspondences
      </summary>
      <p className="text-sm text-muted">
        Same-root annotation revisions are paired automatically. Different roots remain separate
        unless declared here. Exact, unambiguous judgement statements may correspond automatically;
        reusing a J1 label is insufficient.
      </p>
      {annotations.length < 20 && (
        <PairForm
          title="Annotation correspondence"
          before={left}
          after={right}
          onAdd={(a, b, rationale) => {
            const l = before.find((item) => annotationKey(item) === a);
            const r = after.find((item) => annotationKey(item) === b);
            if (l && r)
              onAnnotations([
                ...annotations,
                {
                  kind: annotationKind(l),
                  before_revision_id: l.id,
                  after_revision_id: r.id,
                  rationale,
                },
              ]);
          }}
        />
      )}
      {annotations.map((pair, index) => (
        <p key={index} className="text-xs [overflow-wrap:anywhere]">
          {pair.kind}: {pair.before_revision_id} to {pair.after_revision_id}. {pair.rationale}{' '}
          <Button
            variant="secondary"
            onClick={() => onAnnotations(annotations.filter((_, i) => i !== index))}
          >
            Remove annotation correspondence {index + 1}
          </Button>
        </p>
      ))}
      {judgements.length < 20 && (
        <PairForm
          title="Judgement correspondence"
          before={beforeReport.version.body.key_judgements
            .filter((item) => !judgements.some((pair) => pair.before_judgement_id === item.id))
            .map((item) => ({ value: item.id, label: `${item.id}: ${item.statement}` }))}
          after={afterReport.version.body.key_judgements
            .filter((item) => !judgements.some((pair) => pair.after_judgement_id === item.id))
            .map((item) => ({ value: item.id, label: `${item.id}: ${item.statement}` }))}
          onAdd={(before_judgement_id, after_judgement_id, rationale) =>
            onJudgements([...judgements, { before_judgement_id, after_judgement_id, rationale }])
          }
        />
      )}
      {judgements.map((pair, index) => (
        <p key={index} className="text-xs">
          {pair.before_judgement_id} to {pair.after_judgement_id}. {pair.rationale}{' '}
          <Button
            variant="secondary"
            onClick={() => onJudgements(judgements.filter((_, i) => i !== index))}
          >
            Remove judgement correspondence {index + 1}
          </Button>
        </p>
      ))}
    </details>
  );
}
