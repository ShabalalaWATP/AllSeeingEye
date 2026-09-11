import { CountryMultiSelect } from '@/components/research/CountryMultiSelect';
import { ResearchTimeScope, type ResearchDates } from './ResearchTimeScope';
import { FreshWebSearch } from './FreshWebSearch';
import { ProjectHistory, type ProjectHistoryState } from './ProjectHistory';
import { SourceLanguagePicker } from '@/components/languages/SourceLanguagePicker';
import { RegionalPresets } from './RegionalPresets';
import { GeneralRecordScope } from './GeneralRecordScope';
import { SelectField, TextField } from '@/components/ui/Field';
import { WorkspaceField } from '@/components/ui/WorkspaceField';
import type { Country } from '@/lib/api/geoSchemas';
import type { ReportRequest } from '@/lib/api/reports';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';

export type ResearchFocus = ReportRequest['research_focus'];

interface ScopeProps {
  history?: ProjectHistoryState;
  setHistory?: (value: ProjectHistoryState) => void;
  workspaces: Workspaces;
  teamId: string;
  selectTeam: (id: string) => void;
  countries: readonly Country[];
  selectedCountries: string[];
  setCountries: (value: string[]) => void;
  dates: ResearchDates | null;
  setDates: (value: ResearchDates | null) => void;
  webSearch: boolean;
  setWebSearch: (value: boolean) => void;
  windowHours: string;
  setWindowHours: (value: string) => void;
  selectedLanguages: string[];
  setLanguages: (value: string[]) => void;
  focus: ResearchFocus;
  setFocus: (value: ResearchFocus) => void;
  subject: string;
  setSubject: (value: string) => void;
}

export function ResearchScope(props: ScopeProps) {
  const privateFocus = props.focus === 'document' || props.focus === 'media';
  return (
    <div className="grid min-w-0 gap-5 pt-4 sm:grid-cols-2">
      <WorkspaceField
        workspaces={props.workspaces}
        value={props.teamId}
        onChange={props.selectTeam}
      />
      <div className="grid content-start gap-4">
        <SelectField
          label="Research focus"
          value={props.focus}
          className="min-h-11"
          options={[
            { value: 'general', label: 'General question' },
            { value: 'company', label: 'Company' },
            { value: 'domain', label: 'Domain' },
            { value: 'document', label: 'Private document' },
            { value: 'media', label: 'Private media' },
          ]}
          onChange={(event) => {
            const value = event.target.value;
            if (
              value === 'general' ||
              value === 'company' ||
              value === 'domain' ||
              value === 'document' ||
              value === 'media'
            )
              props.setFocus(value);
          }}
        />
        {(props.focus === 'company' || props.focus === 'domain') && (
          <TextField
            label={props.focus === 'company' ? 'Company name' : 'Domain name'}
            className="min-h-11"
            maxLength={300}
            value={props.subject}
            onChange={(event) => props.setSubject(event.target.value)}
            hint={
              props.focus === 'company'
                ? 'Use a full name or explicit registry identifier, such as GB:01234567 for Companies House or LEI: followed by a legal entity identifier.'
                : 'For example, example.org.'
            }
          />
        )}
      </div>
      {props.focus === 'general' && (
        <CountryMultiSelect
          countries={props.countries}
          value={props.selectedCountries}
          onChange={props.setCountries}
        />
      )}
      {!props.history?.enabled && (
        <ResearchTimeScope
          windowHours={props.windowHours}
          setWindowHours={props.setWindowHours}
          dates={props.dates}
          setDates={props.setDates}
        />
      )}
      <div className="sm:col-span-2">
        {!privateFocus && (
          <FreshWebSearch enabled={props.webSearch} onChange={props.setWebSearch} />
        )}
        {privateFocus && (
          <p className="text-xs text-muted">
            Private input research stays within your selected AI connection. Public web search is
            disabled for attachments.
          </p>
        )}
      </div>
      <details className="min-w-0 sm:col-span-2">
        <summary className="cursor-pointer py-2 text-sm font-medium">
          Advanced source settings{' '}
          <span className="ml-2 text-xs font-normal text-muted">
            Languages, regional presets and specialist records
          </span>
        </summary>
        <div className="space-y-5 pt-4">
          {props.focus === 'general' && (
            <RegionalPresets
              onSelect={(country, languages) => {
                props.setCountries([country]);
                props.setLanguages(languages);
              }}
            />
          )}
          {props.focus === 'general' && props.history && props.setHistory && (
            <ProjectHistory value={props.history} onChange={props.setHistory} />
          )}
          {props.focus === 'general' && (
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
    </div>
  );
}
