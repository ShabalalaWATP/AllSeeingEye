import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import type { BriefDraft } from '@/lib/api/researchBriefSchema';

import { BriefListField } from './BriefListField';

export function BriefQuestionEditor({
  draft,
  change,
}: {
  draft: BriefDraft;
  change: (next: BriefDraft) => void;
}) {
  const requirements = draft.question.requirements;
  const updateRequirement = (index: number, patch: Partial<(typeof requirements)[number]>) =>
    change({
      ...draft,
      question: {
        ...draft.question,
        requirements: requirements.map((row, position) =>
          position === index ? { ...row, ...patch } : row,
        ),
      },
    });
  return (
    <div className="space-y-5">
      <TextField
        label="Brief title"
        required
        maxLength={120}
        value={draft.title}
        onChange={(event) => change({ ...draft, title: event.target.value })}
      />
      <TextAreaField
        label="Main research question"
        required
        maxLength={2000}
        value={draft.question.main}
        onChange={(event) =>
          change({ ...draft, question: { ...draft.question, main: event.target.value } })
        }
      />
      <fieldset className="min-w-0 space-y-3 rounded-lg border border-line p-4">
        <legend className="px-1 text-sm font-semibold">Intelligence requirements</legend>
        <p className="text-xs text-muted">
          Up to 12 stable IDs. Basic allows 3 required, Deep 6, Advanced 12.
        </p>
        {requirements.map((row, index) => (
          <div key={index} className="space-y-3 border-t border-line pt-3">
            <div className="grid gap-3 sm:grid-cols-[10rem_minmax(0,1fr)]">
              <TextField
                label={`Requirement ${index + 1} ID`}
                required
                maxLength={64}
                value={row.id}
                onChange={(event) => updateRequirement(index, { id: event.target.value })}
              />
              <TextField
                label={`Requirement ${index + 1} question`}
                required
                maxLength={500}
                value={row.question}
                onChange={(event) => updateRequirement(index, { question: event.target.value })}
              />
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={row.required}
                  onChange={(event) => updateRequirement(index, { required: event.target.checked })}
                />
                Required
              </label>
              <SelectField
                label={`Requirement ${index + 1} priority`}
                value={String(row.priority)}
                onChange={(event) =>
                  updateRequirement(index, { priority: Number(event.target.value) })
                }
                options={Array.from({ length: 12 }, (_, n) => ({
                  value: String(n + 1),
                  label: String(n + 1),
                }))}
              />
              <Button
                variant="ghost"
                onClick={() =>
                  change({
                    ...draft,
                    question: {
                      ...draft.question,
                      requirements: requirements.filter((_, position) => position !== index),
                    },
                  })
                }
              >
                Remove requirement {index + 1}
              </Button>
            </div>
          </div>
        ))}
        <Button
          variant="secondary"
          disabled={requirements.length >= 12}
          onClick={() =>
            change({
              ...draft,
              question: {
                ...draft.question,
                requirements: [
                  ...requirements,
                  {
                    id: `req-${requirements.length + 1}`,
                    question: '',
                    required: true,
                    priority: requirements.length + 1,
                  },
                ],
              },
            })
          }
        >
          Add requirement
        </Button>
      </fieldset>
      <BriefListField
        label="Excluded questions or claims, one per line"
        maxLength={3000}
        multiline
        values={draft.question.exclusions}
        change={(exclusions) =>
          change({
            ...draft,
            question: {
              ...draft.question,
              exclusions,
            },
          })
        }
      />
    </div>
  );
}
