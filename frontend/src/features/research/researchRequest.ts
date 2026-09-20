/**
 * What a research form holds, what stops it being sent, and the request it becomes. Kept
 * apart from the component so the rules read as rules and the form reads as a form.
 */
import type { Category } from '@/lib/api/eventSchemas';
import type { Country } from '@/lib/api/geoSchemas';
import type { Profile } from '@/lib/api/profile';
import type { Report, ReportRequest, ReportTemplate } from '@/lib/api/reports';
import type { Region } from '@/lib/regions';
import { MAX_RESEARCH_HOURS, researchDateError, type ResearchDates } from '@/lib/researchPeriod';

import type { FollowUpRequest } from '@/lib/followUpScope';
import type { ProjectHistoryState } from './ProjectHistory';
import { recordScopeError } from './recordScope';
import type { useResearchPlan } from './useResearchPlan';

export type ResearchFocus = ReportRequest['research_focus'];
export interface Parent {
  report: Report;
  request: FollowUpRequest;
}

export interface ResearchDraft {
  question: string;
  mode: NonNullable<ReportRequest['research_mode']>;
  focus: ResearchFocus;
  subject: string;
  countries: string[];
  regions: Region[];
  themes: Category[];
  conflictId: string;
  hazard: string;
  dates: ResearchDates | null;
  windowHours: string;
  languages: string[];
  webSearch: boolean;
  reportLanguage: NonNullable<ReportRequest['report_language']>;
  reportStyle: NonNullable<ReportRequest['report_style']>;
  history: ProjectHistoryState;
  inputId: string | null;
}

export interface ResearchContext {
  parent: Parent | undefined;
  countries: readonly Country[];
  historical: boolean;
  interval: { since: string; until: string } | null;
  plan: Pick<ReturnType<typeof useResearchPlan>, 'customised' | 'current' | 'snapshot' | 'request'>;
}

export const isPrivateFocus = (focus: ResearchFocus) => focus === 'document' || focus === 'media';

export function initialDraft(
  preferences: Profile,
  parent: Parent | undefined,
  initialQuestion: string,
  initialDates: ResearchDates | null | undefined,
  initialCountry: string,
): ResearchDraft {
  const request = parent?.request;
  return {
    question: initialQuestion,
    mode: request?.research_mode ?? preferences.research_mode,
    focus: request?.research_focus ?? 'general',
    subject: request?.research_subject ?? '',
    countries:
      request?.countries ??
      (request?.country ? [request.country] : !parent && initialCountry ? [initialCountry] : []),
    regions: request?.regions ?? [],
    themes: [],
    conflictId: '',
    hazard: '',
    dates:
      request?.research_since && request.research_until
        ? { since: request.research_since, until: request.research_until }
        : (initialDates ?? null),
    windowHours: String(request?.window_hours ?? preferences.research_window_days * 24),
    languages: request?.research_languages ?? preferences.research_languages,
    webSearch: request?.research_web_search ?? false,
    reportLanguage: request?.report_language ?? preferences.report_language,
    reportStyle: request?.report_style ?? preferences.report_style,
    history: { enabled: false, firstYear: '2000', lastYear: '2021' },
    inputId: null,
  };
}

/** The first reason the draft cannot be sent, in the order a reader meets the fields. */
export function researchIssue(draft: ResearchDraft, ctx: ResearchContext): string | null {
  const { parent, countries, historical, interval, plan } = ctx;
  const privateFocus = isPrivateFocus(draft.focus);
  const general = draft.focus === 'general';
  const question = draft.question.trim();
  if (!question) return 'Enter a question to research.';
  if (question.length > 1000) return 'Keep your question within 1,000 characters.';
  if (
    !parent &&
    general &&
    (draft.countries.length > 8 ||
      draft.countries.some((code) => !countries.some((item) => item.iso2 === code)))
  )
    return 'Choose up to eight available countries, or use worldwide.';
  if (draft.languages.length === 0) return 'Select at least one search language.';
  if ((draft.focus === 'company' || draft.focus === 'domain') && !draft.subject.trim())
    return `Enter a ${draft.focus === 'company' ? 'company name' : 'domain name'}.`;
  if (privateFocus && !draft.inputId && !parent?.report.version.evidence.length)
    return 'Attach a document or media file before starting this research.';
  if (!parent && !privateFocus && plan.customised && !plan.current)
    return 'Preview your edited collection plan before starting research.';
  if (!parent && !historical) {
    if (draft.dates) {
      const dateError = researchDateError(draft.dates);
      if (dateError) return dateError;
    } else {
      const hours = Number(draft.windowHours);
      if (!Number.isInteger(hours) || hours <= 0 || hours > MAX_RESEARCH_HOURS)
        return 'Choose a valid search period of up to two years.';
    }
  }
  if (
    historical &&
    (!interval ||
      !plan.current ||
      !plan.snapshot?.tasks.some(
        (task) => task.source_id === 'research-aiddata-projects' && task.selected && task.supported,
      ))
  )
    return 'Choose valid project years and preview a supported selected source.';
  if (!parent && general) return recordScopeError(draft.subject.trim(), draft.countries);
  return null;
}

export function researchRequest(
  draft: ResearchDraft,
  ctx: ResearchContext,
  template: ReportTemplate,
  teamId: string,
): ReportRequest {
  const { parent, historical, interval, plan } = ctx;
  const privateFocus = isPrivateFocus(draft.focus);
  const general = draft.focus === 'general';
  return {
    disclose_area_to_provider: false,
    template: template.id,
    question: draft.question.trim(),
    research_mode: draft.mode,
    report_language: draft.reportLanguage,
    report_style: draft.reportStyle,
    research_languages: draft.languages,
    research_focus: draft.focus,
    research_subject: !privateFocus && draft.subject.trim() ? draft.subject.trim() : null,
    ...(historical
      ? {
          research_since: interval?.since ?? null,
          research_until: interval?.until ?? null,
          research_time_basis: 'recorded_time' as const,
        }
      : draft.dates
        ? { research_since: draft.dates.since, research_until: draft.dates.until }
        : { window_hours: Number(draft.windowHours) }),
    devils_advocacy: draft.mode !== 'quick',
    ...(general
      ? {
          countries: draft.countries,
          regions: draft.regions,
          ...(draft.conflictId ? { conflict: draft.conflictId } : {}),
          ...(draft.hazard ? { hazard: draft.hazard } : {}),
        }
      : {}),
    ...(!privateFocus && draft.themes.length > 0 ? { categories: draft.themes } : {}),
    research_web_search: !privateFocus && draft.webSearch,
    ...(teamId ? { team_id: teamId } : {}),
    ...(!parent && !privateFocus ? plan.request : {}),
    ...parent?.request,
    ...(privateFocus && draft.inputId ? { research_input_id: draft.inputId } : {}),
  };
}
