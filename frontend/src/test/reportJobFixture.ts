import type { ReportJob, ReportJobCreate } from '@/lib/api/reportJobs';

export async function readReportJobRequest(request: Request) {
  const body = (await request.json()) as ReportJobCreate;
  return body.report;
}

export const jobId = '11111111-2222-4333-8444-555555555555';
export function reportJob(overrides: Partial<ReportJob> = {}): ReportJob {
  return {
    id: jobId,
    revision: 1,
    title: 'Researching the available evidence',
    status: 'running',
    stage: 'drafting',
    created_at: '2026-09-11T10:00:00Z',
    updated_at: '2026-09-11T10:01:00Z',
    team_id: null,
    report_id: null,
    model: 'configured-research-model',
    reasoning_effort: 'high',
    error: null,
    can_resume: false,
    completed_sections: 1,
    total_sections: 3,
    sections: [
      {
        id: 'section-1',
        title: 'Available observations',
        kind: 'topic',
        status: 'completed',
        reporting: ['A public observation was retained.'],
        assessment: 'Coverage remains incomplete.',
        citations: ['E1', 'E2'],
        error: null,
      },
    ],
    usage: {
      calls: 2,
      max_calls: 12,
      output_tokens: 1200,
      output_allowance: 18000,
      uncertain_calls: 0,
    },
    ...overrides,
  };
}
