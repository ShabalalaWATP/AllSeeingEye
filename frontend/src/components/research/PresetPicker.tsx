import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';
import {
  editablePresetDefinition,
  fetchResearchPresets,
  type PresetDepth,
  type PresetGroup,
  type PresetItem,
  type PresetLens,
} from '@/lib/api/researchPresets';
import type { BriefDraft } from '@/lib/api/researchBriefSchema';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

import { PresetReadiness } from './PresetReadiness';
import { presetDraft } from './presetDraft';

const groups: { id: PresetGroup; label: string }[] = [
  { id: 'conflict', label: 'Conflict' },
  { id: 'cyber', label: 'Cyber' },
  { id: 'economy', label: 'Economy' },
  { id: 'cross_cutting', label: 'Cross-cutting' },
];
const depthOptions = [
  { value: 'quick', label: 'Basic (up to 3 required)' },
  { value: 'detailed', label: 'Deep (up to 6 required)' },
  { value: 'advanced', label: 'Advanced (up to 12 required)' },
];
const depthLimit = { quick: 3, detailed: 6, advanced: 12 };
const labelLens = (value: string) =>
  value.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase());

export function PresetPicker({
  draft,
  onApply,
}: {
  draft: BriefDraft;
  onApply: (next: BriefDraft) => boolean;
}) {
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  const loader = useCallback(() => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    return fetchResearchPresets(controller.signal);
  }, []);
  const { data, loading, error, reload } = useScopedResource(loader);
  const [query, setQuery] = useState('');
  const [group, setGroup] = useState<'all' | PresetGroup>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [depth, setDepth] = useState<PresetDepth>('detailed');
  const [lens, setLens] = useState<PresetLens>('general');
  const [requirementIds, setRequirementIds] = useState<string[]>([]);
  const [sourceIds, setSourceIds] = useState<string[]>([]);
  const [applied, setApplied] = useState<PresetItem | null>(null);
  const [omittedIds, setOmittedIds] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const mapPinned = Boolean(draft.scope.area ?? draft.scope.map_origin ?? draft.scope.map_view_id);
  const items = data?.items ?? [];
  const terms = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const visible = items.filter((item) => {
    const preset = item.preset;
    if (mapPinned && preset.id !== 'area-custom') return false;
    if (group !== 'all' && preset.group !== group) return false;
    const searchable = [
      preset.id,
      preset.title,
      preset.purpose,
      preset.question,
      ...preset.keywords,
    ]
      .join(' ')
      .toLocaleLowerCase();
    return terms.every((term) => searchable.includes(term));
  });
  const selected = visible.find((item) => item.preset.id === selectedId) ?? null;
  const choose = (item: PresetItem) => {
    setSelectedId(item.preset.id);
    setDepth(item.preset.default_depth);
    setLens(item.preset.default_lens);
    setRequirementIds(item.preset.requirements.map((row) => row.id));
    setSourceIds([]);
    setProblem(null);
  };
  const toggle = (current: string[], value: string, selected: boolean) =>
    selected ? [...current, value] : current.filter((item) => item !== value);
  const selectedRequired =
    selected?.preset.requirements.filter((row) => row.required && requirementIds.includes(row.id))
      .length ?? 0;
  const selectionIssue = !selected
    ? null
    : requirementIds.length === 0
      ? 'Select at least one requirement.'
      : selectedRequired > depthLimit[depth]
        ? `Reduce required questions to ${depthLimit[depth]} for this depth. Nothing is removed automatically.`
        : selected.readiness.source_selection_required && sourceIds.length === 0
          ? 'Choose at least one current candidate source.'
          : null;
  const apply = async () => {
    if (!selected || selectionIssue || busy) return;
    setBusy(true);
    setProblem(null);
    const controller = new AbortController();
    request.current = controller;
    try {
      const result = await editablePresetDefinition(
        selected,
        {
          depth,
          lens,
          selectedRequirementIds: requirementIds,
          ...(selected.readiness.source_selection_required ? { selectedSourceIds: sourceIds } : {}),
        },
        controller.signal,
      );
      const next = presetDraft(result.definition, draft);
      if (controller.signal.aborted || !onApply(next)) return;
      setApplied(selected);
      setOmittedIds(result.omitted_requirement_ids);
    } catch (caught) {
      setProblem(describeError(caught));
    } finally {
      setBusy(false);
      request.current = null;
    }
  };
  return (
    <section aria-label="Research preset library" className="space-y-4 border-b border-line pb-5">
      <fieldset disabled={busy} className="min-w-0 space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 className="font-semibold">Start from a reviewed preset</h3>
            <p className="text-xs text-muted">
              Choose a starter, review its gaps, then apply it to an editable brief.
            </p>
          </div>
          <Link to="/research?brief=library" className="text-sm text-ember underline">
            My briefs
          </Link>
        </div>
        {loading && <LoadingNote label="Loading research presets" />}
        {error && (
          <Alert tone="error">
            {describeError(error)}{' '}
            <Button variant="secondary" onClick={() => void reload()}>
              Retry presets
            </Button>
          </Alert>
        )}
        {data && (
          <>
            {mapPinned && (
              <p className="text-xs text-muted">
                The saved polygon stays pinned. Only the area starter applies to this map.
              </p>
            )}
            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_11rem]">
              <TextField
                label="Search presets"
                value={query}
                maxLength={120}
                onChange={(event) => setQuery(event.target.value)}
              />
              <SelectField
                label="Preset group"
                value={group}
                onChange={(event) => setGroup(event.target.value as typeof group)}
                options={[
                  { value: 'all', label: 'All groups' },
                  ...groups.map((row) => ({ value: row.id, label: row.label })),
                ]}
              />
            </div>
            <div className="grid gap-5 lg:grid-cols-[minmax(0,16rem)_minmax(0,1fr)]">
              <div
                className="max-h-80 overflow-y-auto border-l border-line pl-3"
                aria-label="Preset results"
              >
                {visible.length === 0 && (
                  <p className="text-sm text-muted">No presets match this search.</p>
                )}
                {groups.map((entry) => {
                  const rows = visible.filter((item) => item.preset.group === entry.id);
                  return (
                    rows.length > 0 && (
                      <section
                        key={entry.id}
                        className="mb-3"
                        aria-label={`${entry.label} presets`}
                      >
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted">
                          {entry.label}
                        </h4>
                        <ul className="mt-1 space-y-1">
                          {rows.map((item) => (
                            <li key={item.preset.id}>
                              <button
                                type="button"
                                aria-pressed={selectedId === item.preset.id}
                                className="w-full rounded px-2 py-1.5 text-left text-sm text-text hover:bg-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ember aria-pressed:bg-surface-2"
                                onClick={() => choose(item)}
                              >
                                {item.preset.title}
                              </button>
                            </li>
                          ))}
                        </ul>
                      </section>
                    )
                  );
                })}
              </div>
              <div className="min-w-0">
                {selected ? (
                  <section aria-label="Selected preset details" className="space-y-4">
                    <div>
                      <h4 className="font-semibold text-text">{selected.preset.title}</h4>
                      <p className="mt-1 text-sm text-muted">{selected.preset.purpose}</p>
                      <p className="mt-1 text-xs text-muted">
                        Version {selected.preset.version} · Reviewed {selected.preset.reviewed_on}
                      </p>
                    </div>
                    <PresetReadiness
                      item={selected}
                      draft={draft}
                      applied={applied?.preset.id === selected.preset.id}
                    />
                    <div className="grid gap-3 sm:grid-cols-2">
                      <SelectField
                        label="Preset depth"
                        value={depth}
                        onChange={(event) => setDepth(event.target.value as PresetDepth)}
                        options={depthOptions}
                      />
                      <SelectField
                        label="Preset lens"
                        value={lens}
                        onChange={(event) => setLens(event.target.value as PresetLens)}
                        options={selected.preset.lens_choices.map((value) => ({
                          value,
                          label: labelLens(value),
                        }))}
                      />
                    </div>
                    {lens === 'actor_perspective' && (
                      <p className="text-xs text-muted">
                        Actor perspective examines stated aims and claims without endorsement or a
                        preferred factual conclusion. Evidence standards do not change.
                      </p>
                    )}
                    <fieldset className="space-y-1">
                      <legend className="text-xs font-semibold">Requirements to include</legend>
                      {selected.preset.requirements.map((row) => (
                        <label key={row.id} className="flex gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={requirementIds.includes(row.id)}
                            onChange={(event) =>
                              setRequirementIds(
                                toggle(requirementIds, row.id, event.target.checked),
                              )
                            }
                          />
                          <span>
                            {row.question}{' '}
                            <span className="text-xs text-muted">
                              ({row.id}
                              {row.required ? ', required' : ', optional'})
                            </span>
                          </span>
                        </label>
                      ))}
                    </fieldset>
                    {selected.readiness.source_selection_required && (
                      <fieldset className="space-y-1">
                        <legend className="text-xs font-semibold">
                          Choose candidate sources (maximum 64)
                        </legend>
                        <div className="max-h-40 space-y-1 overflow-y-auto">
                          {selected.readiness.candidate_provider_ids.map((id) => (
                            <label key={id} className="flex gap-2 text-xs">
                              <input
                                type="checkbox"
                                checked={sourceIds.includes(id)}
                                disabled={!sourceIds.includes(id) && sourceIds.length >= 64}
                                onChange={(event) =>
                                  setSourceIds(toggle(sourceIds, id, event.target.checked))
                                }
                              />
                              {id}
                            </label>
                          ))}
                        </div>
                      </fieldset>
                    )}
                    {selectionIssue && <p className="text-xs text-ember">{selectionIssue}</p>}
                    {problem && <Alert tone="error">{problem}</Alert>}
                    <Button
                      disabled={!!selectionIssue || busy}
                      busy={busy}
                      onClick={() => void apply()}
                    >
                      Apply preset to draft
                    </Button>
                    <p className="text-xs text-muted">
                      Applying replaces current draft settings. Nothing is saved or run.
                    </p>
                  </section>
                ) : (
                  <p className="text-sm text-muted">
                    Select a preset to inspect its coverage and starting settings.
                  </p>
                )}
              </div>
            </div>
            {applied && (
              <p role="status" className="text-sm text-ember">
                {applied.preset.title} applied to the editable draft. Nothing has been saved or run.
                {omittedIds.length > 0 && ` Omitted requirements: ${omittedIds.join(', ')}.`}
              </p>
            )}
          </>
        )}
      </fieldset>
    </section>
  );
}
