/**
 * Where the research is saved and the source settings most questions never touch:
 * languages, regional presets, project history and specialist records.
 */
import { SourceLanguagePicker } from '@/components/languages/SourceLanguagePicker';
import { WorkspaceField } from '@/components/ui/WorkspaceField';
import type { Country } from '@/lib/api/geoSchemas';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';

import { GeneralRecordScope } from './GeneralRecordScope';
import { ProjectHistory, type ProjectHistoryState } from './ProjectHistory';
import { RegionalPresets } from './RegionalPresets';
import type { ResearchFocus } from './researchRequest';

export type { ResearchFocus } from './researchRequest';

interface ScopeProps {
  history: ProjectHistoryState;
  setHistory: (value: ProjectHistoryState) => void;
  workspaces: Workspaces;
  teamId: string;
  selectTeam: (id: string) => void;
  countries: readonly Country[];
  selectedCountries: string[];
  setCountries: (value: string[]) => void;
  selectedLanguages: string[];
  setLanguages: (value: string[]) => void;
  focus: ResearchFocus;
  subject: string;
  setSubject: (value: string) => void;
}

export function ResearchScope(props: ScopeProps) {
  const general = props.focus === 'general';
  return (
    <>
      <WorkspaceField
        workspaces={props.workspaces}
        value={props.teamId}
        onChange={props.selectTeam}
      />
      <details className="min-w-0 rounded-xl border border-line bg-ground px-4">
        <summary className="cursor-pointer py-3 text-sm font-medium">
          Advanced source settings{' '}
          <span className="ml-2 text-xs font-normal text-muted">
            Languages, regional presets and specialist records
          </span>
        </summary>
        <div className="space-y-5 pt-2 pb-4">
          {general && (
            <RegionalPresets
              onSelect={(country, languages) => {
                props.setCountries([country]);
                props.setLanguages(languages);
              }}
            />
          )}
          {general && <ProjectHistory value={props.history} onChange={props.setHistory} />}
          {general && (
            <GeneralRecordScope
              subject={props.subject}
              setSubject={props.setSubject}
              selectedCountries={props.selectedCountries}
              countries={props.countries}
            />
          )}
          <SourceLanguagePicker selected={props.selectedLanguages} onChange={props.setLanguages} />
        </div>
      </details>
    </>
  );
}
