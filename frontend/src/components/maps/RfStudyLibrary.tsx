import { useEffect, useRef, useState } from 'react';
import type { RfDraft } from '@/lib/map/rfDraft';
import { readRfStudy, type RfStudySnapshot } from '@/lib/map/rfStudy';
import { subscribeRfWorkspaceReset } from '@/lib/map/rfWorkspaceAccess';
import { WorkspaceField } from '@/components/ui/WorkspaceField';
import { useWorkspaces, useWorkspaceSelection } from '@/lib/hooks/useWorkspaces';
import { RfStudyComparison } from './RfStudyComparison';
import { useRfStudyLibrary } from './useRfStudyLibrary';

export interface RfStudyWorkspace {
  baseline: RfStudySnapshot | null;
  setBaseline: (value: RfStudySnapshot | null) => void;
  restoreStudy: (value: RfStudySnapshot) => void;
}
export function RfStudyLibrary({
  workspace,
  draft,
  snapshot,
}: {
  workspace: RfStudyWorkspace;
  draft: RfDraft;
  snapshot: () => RfStudySnapshot;
}) {
  const authority = useRef(0);
  const library = useRfStudyLibrary();
  const workspaces = useWorkspaces();
  const scope = useWorkspaceSelection(workspaces);
  const [title, setTitle] = useState('Radio study');
  const [selected, setSelected] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const file = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const clear = () => {
      authority.current++;
      setTitle('Radio study');
      setSelected('');
      setError(null);
    };
    const unsubscribe = subscribeRfWorkspaceReset(clear);
    return () => {
      clear();
      unsubscribe();
    };
  }, []);
  const item = library.items.find((value) => value.id === selected);
  const capture = (action: (value: RfStudySnapshot) => void) => {
    try {
      action(snapshot());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Check study inputs.');
    }
  };
  const baseline = workspace.baseline;
  return (
    <details className="rounded-lg border border-line p-3 text-xs">
      <summary className="cursor-pointer">Saved studies and comparison</summary>
      <div className="mt-3 space-y-3">
        <p className="rf-help">
          Save inputs, a frozen result summary and bounded terrain samples when available. Reopen
          restores the setup; analyse again to rebuild detailed profiles and map overlays. Imports
          are unverified scenarios, not measured evidence.
        </p>
        <WorkspaceField
          workspaces={workspaces}
          value={scope.teamId}
          onChange={scope.select}
          disabled={library.busy}
        />
        <p className="rf-help">
          New studies and duplicates use the selected workspace. Updating a saved study keeps its
          existing access scope.
        </p>
        <label className="rf-field">
          <span>Study name</span>
          <input value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <div className="flex flex-wrap gap-2">
          <button
            className="rf-secondary-button"
            type="button"
            disabled={library.busy || !title.trim() || !scope.ready}
            onClick={() =>
              capture(
                (value) =>
                  void library.save(title.trim(), value, undefined, scope.teamId || undefined),
              )
            }
          >
            Save new study
          </button>
          <button
            className="rf-secondary-button"
            type="button"
            disabled={library.busy}
            onClick={() => void library.refresh()}
          >
            Load saved studies
          </button>
          <button
            className="rf-secondary-button"
            type="button"
            onClick={() => capture(workspace.setBaseline)}
          >
            Set comparison baseline
          </button>
        </div>
        {library.items.length > 0 && (
          <>
            <label className="rf-field">
              <span>Saved radio study</span>
              <select value={selected} onChange={(e) => setSelected(e.target.value)}>
                <option value="">Choose a study</option>
                {library.items.map((study) => (
                  <option key={study.id} value={study.id}>
                    {study.title} ({workspaces.label(study.teamId)})
                  </option>
                ))}
              </select>
            </label>
            {item && (
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rf-secondary-button"
                  onClick={() => {
                    workspace.restoreStudy(item.snapshot);
                    setTitle(item.title);
                  }}
                >
                  Reopen
                </button>
                <button
                  type="button"
                  className="rf-secondary-button"
                  onClick={() => workspace.setBaseline(item.snapshot)}
                >
                  Compare against
                </button>
                <button
                  type="button"
                  className="rf-secondary-button"
                  disabled={library.busy || !scope.ready}
                  onClick={() =>
                    void library.save(
                      `${item.title.slice(0, 110)} copy`,
                      item.snapshot,
                      undefined,
                      scope.teamId || undefined,
                    )
                  }
                >
                  Duplicate
                </button>
                <button
                  type="button"
                  className="rf-secondary-button"
                  disabled={library.busy || !title.trim()}
                  onClick={() => capture((value) => void library.save(title.trim(), value, item))}
                >
                  Update selected
                </button>
                <button
                  type="button"
                  className="rf-text-button"
                  disabled={library.busy}
                  onClick={() => void library.remove(item.id)}
                >
                  Delete selected study
                </button>
              </div>
            )}
          </>
        )}
        {library.hasMore && (
          <button
            type="button"
            className="rf-secondary-button"
            disabled={library.busy}
            onClick={() => void library.loadMore()}
          >
            Load more radio studies
          </button>
        )}
        {baseline && (
          <RfStudyComparison
            baseline={baseline}
            draft={draft}
            current={snapshot}
            onClear={() => workspace.setBaseline(null)}
          />
        )}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rf-secondary-button"
            onClick={() =>
              capture((value) => {
                const url = URL.createObjectURL(
                  new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }),
                );
                const link = document.createElement('a');
                link.href = url;
                link.download = 'radio-study.json';
                link.click();
                setTimeout(() => URL.revokeObjectURL(url), 1000);
              })
            }
          >
            Export study JSON
          </button>
          <button
            type="button"
            className="rf-secondary-button"
            onClick={() => file.current?.click()}
          >
            Import study JSON
          </button>
          <input
            ref={file}
            aria-label="Import radio study file"
            className="sr-only"
            type="file"
            accept="application/json,.json"
            onChange={(e) => {
              const chosen = e.target.files?.[0];
              e.target.value = '';
              if (!chosen) return;
              if (chosen.size > 128 * 1024) {
                setError('Radio study exceeds 128 KiB.');
                return;
              }
              const importAuthority = authority.current;
              void chosen
                .text()
                .then((text) => {
                  if (importAuthority !== authority.current) return;
                  workspace.restoreStudy(readRfStudy(text));
                  setError(null);
                })
                .catch(() => {
                  if (importAuthority === authority.current)
                    setError('Invalid or unsupported radio study.');
                });
            }}
          />
        </div>
        {(error ?? library.message) && <p role="alert">{error ?? library.message}</p>}
      </div>
    </details>
  );
}
