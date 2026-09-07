import { useCallback, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import {
  annotationKey,
  annotationKind,
  annotationRoot,
  annotationTitle,
  fetchAnnotation,
  listAnnotations,
} from './comparisonSelection';
import type { AnnotationKind, ComparisonAnnotation } from './comparisonSelection';
interface ChoiceProps {
  value: ComparisonAnnotation;
  selected: ComparisonAnnotation[];
  onToggle: (value: ComparisonAnnotation) => void;
}
function Choice({ value, selected, onToggle }: ChoiceProps) {
  const checked = selected.some((item) => annotationKey(item) === annotationKey(value));
  return (
    <label className="flex items-start gap-2 text-sm">
      <input
        type="checkbox"
        checked={checked}
        disabled={
          !checked &&
          selected.length >= 20 &&
          !selected.some(
            (item) =>
              annotationKind(item) === annotationKind(value) &&
              annotationRoot(item) === annotationRoot(value),
          )
        }
        onChange={() => onToggle(value)}
      />
      <span>
        Select revision {value.number}: {annotationTitle(value)}
        <span className="block text-xs text-muted">
          {value.id} / Author {value.authored_by} / {value.created_at}
        </span>
      </span>
    </label>
  );
}
function RevisionBrowser({ value, selected, onToggle }: ChoiceProps) {
  const [id, setId] = useState(value.id);
  const request = useScopedRequest();
  const loader = useCallback(() => fetchAnnotation(value, id, request()), [value, id, request]);
  const resource = useScopedResource(loader);
  return (
    <div className="space-y-3 border-l border-line pl-3">
      {resource.loading && <LoadingNote label="Loading exact revision" />}
      {resource.error && (
        <Alert tone="error">
          {describeError(resource.error)}{' '}
          <Button variant="secondary" onClick={() => void resource.reload()}>
            Retry exact revision
          </Button>
        </Alert>
      )}
      {resource.data && (
        <>
          <Choice value={resource.data} selected={selected} onToggle={onToggle} />
          <p className="text-xs whitespace-pre-wrap">
            {'reason' in resource.data ? resource.data.reason : resource.data.rationale}
          </p>
          {resource.data.previous_id && (
            <Button
              variant="secondary"
              onClick={() => {
                const previous = resource.data?.previous_id;
                if (previous) setId(previous);
              }}
            >
              Previous revision
            </Button>
          )}
          {id !== value.id && (
            <Button variant="secondary" onClick={() => setId(value.id)}>
              Return to opened revision {value.number}
            </Button>
          )}
        </>
      )}
    </div>
  );
}
export function ComparisonRevisionPicker({
  reportId,
  version,
  selected,
  onChange,
}: {
  reportId: string;
  version: number;
  selected: ComparisonAnnotation[];
  onChange: (values: ComparisonAnnotation[]) => void;
}) {
  const [kind, setKind] = useState<AnnotationKind>('claim');
  const [offset, setOffset] = useState(0);
  const [opened, setOpened] = useState<string | null>(null);
  const request = useScopedRequest();
  const loader = useCallback(
    () => listAnnotations(kind, reportId, version, offset, request()),
    [kind, reportId, version, offset, request],
  );
  const resource = useScopedResource(loader);
  const toggle = (value: ComparisonAnnotation) => {
    const key = annotationKey(value);
    if (selected.some((item) => annotationKey(item) === key)) {
      onChange(selected.filter((item) => annotationKey(item) !== key));
      return;
    }
    const others = selected.filter(
      (item) =>
        annotationKind(item) !== annotationKind(value) ||
        annotationRoot(item) !== annotationRoot(value),
    );
    if (others.length < 20) onChange([...others, value]);
  };
  return (
    <div className="space-y-3">
      <p className="text-xs text-muted">
        Choose up to 20 exact revisions on this side. Current inventory entries are suggestions
        only; selecting one freezes its displayed revision ID. Earlier revisions remain available
        below. Selecting another revision of the same root replaces its selection on this side.
      </p>
      <SelectField
        label="Annotation type"
        value={kind}
        options={[
          { value: 'claim', label: 'Claims' },
          { value: 'identity', label: 'Identity reviews' },
          { value: 'relationship', label: 'Relationship reviews' },
        ]}
        onChange={(event) => {
          setKind(event.target.value as AnnotationKind);
          setOffset(0);
          setOpened(null);
        }}
      />
      {resource.loading && <LoadingNote label="Loading annotation inventory" />}
      {resource.error && (
        <Alert tone="error">
          {describeError(resource.error)}{' '}
          <Button variant="secondary" onClick={() => void resource.reload()}>
            Retry annotation inventory
          </Button>
        </Alert>
      )}
      {resource.data && (
        <>
          {resource.data.total === 0 && (
            <p className="text-sm text-muted">
              No {kind} annotations in this version. Confidence inputs can still be compared.
            </p>
          )}
          {resource.data.items.map((value) => (
            <article className="space-y-2 border-b border-line py-3" key={value.id}>
              <Choice value={value} selected={selected} onToggle={toggle} />
              <Button
                variant="secondary"
                onClick={() => setOpened(opened === value.id ? null : value.id)}
              >
                Browse revisions: {annotationTitle(value)}
              </Button>
              {opened === value.id && (
                <RevisionBrowser value={value} selected={selected} onToggle={toggle} />
              )}
            </article>
          ))}
          {resource.data.total > 20 && (
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - 20))}
              >
                Previous annotation page
              </Button>
              <span className="text-xs">
                {offset + 1} to {offset + resource.data.items.length} of {resource.data.total}
              </span>
              <Button
                variant="secondary"
                disabled={offset + 20 >= resource.data.total}
                onClick={() => setOffset(offset + 20)}
              >
                Next annotation page
              </Button>
            </div>
          )}
        </>
      )}
      {selected.length > 0 && (
        <div>
          <p className="text-sm">{selected.length} of 20 selected on this side</p>
          <ul className="space-y-2">
            {selected.map((value) => (
              <li key={annotationKey(value)} className="text-xs [overflow-wrap:anywhere]">
                {annotationTitle(value)} / Revision {value.number} / {value.id}{' '}
                <Button variant="secondary" onClick={() => toggle(value)}>
                  Remove selected revision {value.id}
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
