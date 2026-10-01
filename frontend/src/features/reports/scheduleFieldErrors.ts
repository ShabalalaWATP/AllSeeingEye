/**
 * Where each rejected subscription request path belongs on the subscription form. Name and
 * question sit beside their own fields; composite pickers link to the step that holds them.
 */
import type { FieldSpec } from '@/lib/api/fieldErrors';

export const SCHEDULE_FIELDS = {
  name: 'Subscription name',
  question: 'Question',
  depth: { label: 'How deep to go', paths: ['research_mode'], target: 'subscription-depth' },
  place: {
    label: 'Where to look',
    paths: ['country_iso', 'country_isos', 'regions'],
    target: 'subscription-countries',
  },
  themes: { label: 'Which themes', paths: ['categories'], target: 'subscription-themes' },
  coverage: {
    label: 'Conflict or disaster',
    paths: ['conflict_id', 'hazard', 'research_area', 'disclose_area_to_provider'],
    target: 'subscription-coverage',
  },
  sources: {
    label: 'What to read',
    paths: ['research_web_search'],
    target: 'subscription-sources',
  },
  timing: {
    label: 'When to run',
    paths: [
      'hour_utc',
      'timezone',
      'local_hour',
      'local_minute',
      'cadence',
      'weekday',
      'monthday',
      'anchor_month',
      'window_hours',
      'avoid_repetition',
      'notify_on_change',
    ],
    target: 'subscription-timing',
  },
  advanced: {
    label: 'Advanced scope and sources',
    paths: [
      'template_id',
      'plan_id',
      'team_id',
      'collection_policy',
      'research_languages',
      'research_focus',
      'research_subject',
      'research_source_ids',
      'enabled',
    ],
    target: 'subscription-advanced',
  },
} satisfies Record<string, FieldSpec>;
