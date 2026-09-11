import type { ReportJob } from '@/lib/api/reportJobs';

export const jobStatus: Record<ReportJob['status'], string> = {
  queued: 'Queued',
  running: 'In progress',
  paused: 'Paused',
  completed: 'Completed',
  needs_review: 'Needs review',
  failed: 'Stopped with an error',
};
const stages: Record<string, string> = {
  preparing: 'Preparing research',
  planning: 'Planning the evidence search',
  collecting: 'Collecting sources',
  drafting: 'Writing sections',
  summarising: 'Bringing the findings together',
  validating: 'Checking the report',
  saving: 'Saving the report',
  completed: 'Report saved',
  paused: 'Research paused',
};
export const jobStage = (stage: string) =>
  stages[stage] ?? stage.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase());
export const jobRunning = (job: ReportJob) => job.status === 'queued' || job.status === 'running';
export const jobsRunning = (jobs: ReportJob[]) => jobs.some(jobRunning);
