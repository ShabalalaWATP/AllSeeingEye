/**
 * Links into a team board thread, shared by features that point at team work.
 * Parsed values only select what to show; the server re-checks every subject.
 */
import type { BoardSubjectInput, BoardSubjectKind } from '@/lib/api/teamBoard';

export interface BoardLink {
  teamId: string;
  postId: string | null;
  subject: BoardSubjectInput | null;
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const KINDS: readonly BoardSubjectKind[] = ['report_version', 'saved_area', 'drawing_collection'];

function uuid(value: string | null): string | null {
  return value !== null && UUID.test(value) ? value : null;
}

function teamBoard(teamId: string): URLSearchParams {
  return new URLSearchParams({ team: teamId, board: 'thread' });
}

export function teamThreadPath(teamId: string, postId: string): string {
  const params = teamBoard(teamId);
  params.set('post', postId);
  return `/teams?${params.toString()}`;
}

export function startTeamThreadPath(teamId: string, subject: BoardSubjectInput): string {
  const params = teamBoard(teamId);
  params.set('subject', subject.kind);
  params.set('subject_id', subject.id);
  if (subject.version != null) params.set('version', String(subject.version));
  return `/teams?${params.toString()}`;
}

function parseSubject(params: URLSearchParams): BoardSubjectInput | null {
  const kind = KINDS.find((item) => item === params.get('subject'));
  const id = uuid(params.get('subject_id'));
  if (!kind || !id) return null;
  const raw = params.get('version');
  if (kind !== 'report_version') return raw === null ? { kind, id } : null;
  const version = raw !== null && /^[1-9][0-9]{0,5}$/.test(raw) ? Number(raw) : null;
  return version === null ? null : { kind, id, version };
}

export function parseBoardLink(params: URLSearchParams): BoardLink | null {
  const teamId = uuid(params.get('team'));
  if (!teamId || params.get('board') !== 'thread') return null;
  return { teamId, postId: uuid(params.get('post')), subject: parseSubject(params) };
}
