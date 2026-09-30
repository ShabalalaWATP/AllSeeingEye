import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it } from 'vitest';

import type { ResearchPreflight } from '@/lib/api/researchPreflight';

import { BriefPreflightResult } from './BriefPreflightResult';

function preview(): ResearchPreflight {
  return {
    brief_id: 'd73c2988-d2ca-4482-9e39-7269e876eaa0',
    revision: 4,
    title: 'Port review',
    as_of: '2026-09-14T10:00:00Z',
    since: '2026-09-13T10:00:00Z',
    until: '2026-09-14T10:00:00Z',
    scope: {
      country_isos: [],
      focus: 'general',
      subject: null,
      area_sha256: null,
      saved_map_resolution_required: false,
      linked_context_checks_required: false,
    },
    observation_policy: 'relative',
    time_basis: 'publication',
    forecast_horizon_days: null,
    question: 'What changed at the port?',
    requirements: [],
    budget: {
      tier: 'quick',
      required_question_ceiling: 3,
      tier_source_operations: 12,
      tier_collection_seconds: 90,
      source_operation_ceiling: 12,
      collection_second_ceiling: 90,
      model_call_ceiling: 8,
      output_token_ceiling: 12000,
      reservations_made: false,
    },
    source_policy: 'all_eligible',
    sources: [],
    unknown_source_ids: [],
    gaps: [],
    candidate_provider_ids: [],
    known_origin_group_count: 0,
    unknown_origin_capability_count: 0,
    review_reasons: [],
    preview_only: true,
    admission_checked: false,
    source_relevance_ranked: false,
    provider_calls: 0,
    model_calls: 0,
    model_compatibility: 'not_checked',
    policy_version: 'test-v1',
    duration_note: 'Generation duration is unknown.',
    coverage_note: 'Archive coverage is unverified.',
  };
}

it('shows an empty preview without inventing a country, forecast, readiness or reservations', () => {
  render(<BriefPreflightResult preview={preview()} />);
  expect(screen.getByText(/No country filter/)).toBeVisible();
  expect(screen.getByText(/0 required of 0 selected.*Basic allows up to 3/)).toBeVisible();
  expect(screen.getByText(/0 unverified candidates · 0 excluded/)).toBeVisible();
  expect(screen.getByText(/12,000 output tokens. No capacity was reserved/)).toBeVisible();
  expect(screen.getByText(/No provider or model calls were made/)).toBeVisible();
  expect(screen.queryByText(/forecast horizon/)).not.toBeInTheDocument();
  expect(screen.queryByRole('list', { name: 'Preflight gaps' })).not.toBeInTheDocument();
  expect(screen.queryByRole('list', { name: 'Preflight review reasons' })).not.toBeInTheDocument();
  expect(screen.queryByText(/Unknown selected source IDs/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Reduce .*required question/)).not.toBeInTheDocument();
});

it.each([1, 2])(
  'explains exactly %i excess required questions while retaining optional questions',
  (excess) => {
    const data = preview();
    data.requirements = Array.from({ length: 3 + excess }, (_, index) => ({
      id: `q${index + 1}`,
      question: `Required question ${index + 1}`,
      required: true,
      priority: 1,
    }));
    data.requirements.push({
      id: 'context',
      question: 'Optional background',
      required: false,
      priority: 4,
    });
    render(<BriefPreflightResult preview={data} />);
    expect(
      screen.getByText(
        new RegExp(`Reduce ${excess} required question${excess === 1 ? '' : 's'} in`),
      ),
    ).toBeVisible();
    expect(screen.getByText(/No questions are dropped automatically/)).toBeVisible();
    expect(screen.getByText(/Optional background \(optional, priority 4\)/)).toBeVisible();
    expect(
      within(
        screen.getByRole('region', { name: 'Preflight requirements and limits' }),
      ).getAllByRole('listitem'),
    ).toHaveLength(4 + excess);
  },
);

it('retains saved-map admission warnings and distinguishes candidate routes from exclusions', async () => {
  const data = preview();
  data.scope = {
    country_isos: ['GB', 'FR'],
    focus: 'general',
    subject: 'Channel ports',
    area_sha256: 'a'.repeat(64),
    saved_map_resolution_required: true,
    linked_context_checks_required: true,
  };
  data.forecast_horizon_days = 7;
  data.time_basis = 'recorded_time';
  data.source_policy = 'selected_only';
  data.candidate_provider_ids = ['public'];
  data.sources = [
    {
      capability: {
        id: 'public',
        name: 'Public route',
        route: 'public_research',
        support: { constraints: 'Current metadata only.' },
      },
      readiness: 'public_unverified',
      candidate_unverified: true,
      exclusion_reasons: [],
      date_note: 'No archive guarantee.',
    },
    {
      capability: {
        id: 'disabled',
        name: 'Disabled route',
        route: 'public_research',
        support: { constraints: 'Publisher dates only.' },
      },
      readiness: 'disabled',
      candidate_unverified: false,
      exclusion_reasons: ['source_disabled', 'date_unsupported'],
      date_note: 'Interval unsupported.',
    },
  ];
  data.unknown_source_ids = ['unknown-one', 'unknown-two'];
  data.gaps = [{ id: 'primary', name: 'Primary documents', reason: 'No approved route.' }];
  data.review_reasons = ['linked_context_authorisation_not_checked'];
  render(<BriefPreflightResult preview={data} />);
  expect(screen.getByText(/GB, FR · general · Channel ports · Area SHA-256/)).toBeVisible();
  expect(screen.getByText(/recorded time basis · 7-day forecast horizon/)).toBeVisible();
  expect(screen.getByText(/Saved-map geometry must be resolved again/)).toBeVisible();
  expect(
    screen.getByText(/1 unverified candidate · 1 excluded · selected only selection/),
  ).toBeVisible();
  expect(screen.getByText(/Unknown selected source IDs: unknown-one, unknown-two/)).toBeVisible();
  expect(screen.getByRole('list', { name: 'Preflight gaps' })).toHaveTextContent(
    'Primary documents: No approved route.',
  );
  expect(screen.getByRole('list', { name: 'Preflight review reasons' })).toHaveTextContent(
    'linked context authorisation not checked',
  );
  await userEvent.setup().click(screen.getByText('Inspect 2 source routes and exclusions'));
  expect(screen.getByText(/Candidate, unverified · public unverified/)).toBeVisible();
  expect(screen.getByText(/Excluded: source disabled, date unsupported · disabled/)).toBeVisible();
  expect(screen.getByText('Current metadata only. No archive guarantee.')).toBeVisible();
});
