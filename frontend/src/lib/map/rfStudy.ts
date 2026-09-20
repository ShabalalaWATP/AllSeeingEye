import { z } from 'zod';
import { RF_FIELDS, calculateRf, type RfInputs } from './rfPlanning';
import { RF_ENVIRONMENT_DEFAULTS, type RfDraft } from './rfDraft';
import { RF_ENGINEERING_FIELDS } from './rfEngineering';
import { rfPositionSchema, type RfSiteNames } from './rfSites';
import type { Position } from './geoJsonTypes';
import type { RfAnalysis } from './rfAnalysis';
import { hfGroundwaveReceiver } from './hfGroundwaveMap';
import { measure } from './measurements';
import { parseRfEngineering } from './rfEngineering';
import { rfPlannerInputs } from './rfPlannerInputs';
import { directionalRfInputs } from './rfAntenna';
import { resolveRfMode } from './rfAutomation';

const numericText = (min: number, max: number) =>
  z
    .string()
    .max(40)
    .refine(
      (value) =>
        value.trim() !== '' &&
        Number.isFinite(Number(value)) &&
        Number(value) >= min &&
        Number(value) <= max,
      'Numeric value outside the supported range.',
    );
const valuesSchema = z
  .object(
    Object.fromEntries(RF_FIELDS.map((field) => [field.key, numericText(field.min, field.max)])),
  )
  .strict();
const draftSchema = z
  .object({
    antenna: z
      .object({
        enabled: z.boolean(),
        transmitterBearing: numericText(0, 360),
        receiverBearing: numericText(0, 360),
        beamwidth: numericText(1, 180),
        maximumAttenuation: numericText(0, 60),
      })
      .strict()
      .optional(),
    values: valuesSchema,
    presetId: z.string().max(100),
    propagation: z
      .enum(['automatic', 'terrain', 'free-space', 'hf-groundwave', 'hf-skywave'])
      .optional(),
    automaticHfMode: z.enum(['hf-groundwave', 'hf-skywave']).optional(),
    radiusMode: z.enum(['automatic', 'manual']).optional(),
    study: z.enum(['area', 'link']).optional(),
    environment: z
      .object(
        Object.fromEntries(
          Object.keys(RF_ENVIRONMENT_DEFAULTS).map((key) => [key, numericText(0, 10000)]),
        ),
      )
      .strict()
      .optional(),
    engineering: z
      .object(
        Object.fromEntries(
          RF_ENGINEERING_FIELDS.map((field) => [field.key, numericText(field.min, field.max)]),
        ),
      )
      .strict()
      .optional(),
  })
  .strict();
const resultSchema = z
  .object({
    kind: z.enum(['terrain', 'free-space', 'hf-groundwave', 'hf-skywave']),
    status: z.string().max(120),
    distanceKm: z.number().nonnegative().max(50000).nullable(),
    receivedDbm: z.number().min(-1000).max(1000).nullable(),
    marginDb: z.number().min(-1000).max(1000).nullable(),
    sampleCount: z.number().int().nonnegative().max(10000),
    missingSamples: z.number().int().nonnegative().max(10000),
  })
  .strict();
const terrainEvidenceSchema = z
  .object({
    zoom: z.literal(10),
    resolutionM: z.number().positive().max(153),
    samples: z
      .array(
        z.tuple([
          z.number().min(-180).max(180),
          z.number().min(-90).max(90),
          z.number().min(-12000).max(10000).nullable(),
        ]),
      )
      .min(3)
      .max(1000),
    profiles: z
      .array(
        z
          .object({
            bearingDegrees: z.number().min(0).max(360),
            indices: z.array(z.number().int().min(0).max(999)).min(3).max(1000),
            distancesM: z.array(z.number().nonnegative().max(200000)).min(3).max(1000),
          })
          .strict(),
      )
      .min(1)
      .max(24),
  })
  .strict()
  .refine(
    (value) =>
      value.profiles.every(
        (profile) =>
          profile.indices.length === profile.distancesM.length &&
          profile.indices.every((index) => index < value.samples.length) &&
          profile.distancesM.every((distance, index) =>
            index === 0 ? distance === 0 : distance > (profile.distancesM[index - 1] ?? Infinity),
          ),
      ),
    'Invalid terrain evidence profile.',
  );
const snapshotSchema = z
  .object({
    terrainEvidence: terrainEvidenceSchema.optional(),
    schemaVersion: z.literal(1),
    savedAt: z.iso.datetime(),
    draft: draftSchema,
    origin: rfPositionSchema.nullable(),
    receiver: rfPositionSchema.nullable(),
    siteNames: z.object({ origin: z.string().max(80), receiver: z.string().max(80) }).strict(),
    result: resultSchema.nullable(),
    provenance: z
      .object({
        model: z.string().max(200),
        limitations: z.string().max(6000),
        terrainAttribution: z.string().max(2000).nullable(),
        terrainSourceUrl: z
          .literal('https://github.com/tilezen/joerd/blob/master/docs/attribution.md')
          .nullable(),
      })
      .strict(),
  })
  .strict();
export interface RfStudySnapshot {
  terrainEvidence?: z.infer<typeof terrainEvidenceSchema>;
  schemaVersion: 1;
  savedAt: string;
  draft: RfDraft;
  origin: Position | null;
  receiver: Position | null;
  siteNames: RfSiteNames;
  result: z.infer<typeof resultSchema> | null;
  provenance: z.infer<typeof snapshotSchema>['provenance'];
}
/** Imported summaries are untrusted records, never injected as executable map analyses. */
export function parseRfStudy(value: unknown): RfStudySnapshot {
  const text = JSON.stringify(value);
  if (new TextEncoder().encode(text).length > 128 * 1024)
    throw new Error('Radio study exceeds 128 KiB.');
  return snapshotSchema.parse(value) as unknown as RfStudySnapshot;
}
export function readRfStudy(text: string): RfStudySnapshot {
  if (new TextEncoder().encode(text).length > 128 * 1024)
    throw new Error('Radio study exceeds 128 KiB.');
  return parseRfStudy(JSON.parse(text));
}
export function snapshotRfStudy(
  draft: RfDraft,
  origin: Position | null,
  receiver: Position | null,
  siteNames: RfSiteNames,
  analysis: RfAnalysis | null,
): RfStudySnapshot {
  const mode = resolveRfMode(draft);
  const configured = rfPlannerInputs(draft, origin, draft.study === 'area' ? null : receiver);
  if (configured.error) throw new Error(configured.error);
  let terrainEvidence: RfStudySnapshot['terrainEvidence'];
  let result: RfStudySnapshot['result'] = null;
  const provenance: RfStudySnapshot['provenance'] = {
    model: mode,
    limitations:
      'Planning scenario only. Results are not field measurements or guaranteed reception. Reopen restores inputs; run analysis to rebuild map results.',
    terrainAttribution: null,
    terrainSourceUrl: null,
  };
  if (analysis?.kind === 'terrain') {
    const { terrain, elevations, plan } = analysis;
    terrainEvidence = {
      zoom: elevations.zoom,
      resolutionM: elevations.resolution_m,
      samples: plan.positions.map((position, index) => [
        position[0],
        position[1],
        elevations.elevations_m[index] ?? null,
      ]),
      profiles: plan.profiles,
    };
    result = {
      kind: 'terrain',
      status: terrain.path?.status ?? 'sampled sectors',
      distanceKm: terrain.maxDistanceKm,
      receivedDbm: terrain.path?.receivedDbm ?? null,
      marginDb: terrain.path?.planningMarginDb ?? terrain.path?.marginDb ?? null,
      sampleCount: terrain.sampleCount,
      missingSamples: terrain.missingSamples,
    };
    provenance.model = 'ASE sampled terrain/Fresnel and single-edge screen v1';
    provenance.terrainAttribution = elevations.attribution;
    provenance.terrainSourceUrl =
      'https://github.com/tilezen/joerd/blob/master/docs/attribution.md';
    provenance.limitations += ' ' + elevations.limitations;
  } else if (analysis?.kind === 'hf-groundwave') {
    const receiverDistance = analysis.receiver
      ? measure([analysis.origin, analysis.receiver], 'distance').metres / 1000
      : null;
    const received =
      receiverDistance === null ? null : hfGroundwaveReceiver(analysis.result, receiverDistance);
    result = {
      kind: 'hf-groundwave',
      status: received
        ? received.interpolated
          ? 'interpolated groundwave receiver'
          : 'sampled groundwave receiver'
        : 'calculated groundwave curve',
      distanceKm: received?.distanceKm ?? analysis.result.samples.at(-1)?.distance_km ?? null,
      receivedDbm: received?.receivedDbm ?? null,
      marginDb: received
        ? received.receivedDbm -
          analysis.input.sensitivityDbm -
          (analysis.engineering?.reserveDb ?? 0)
        : null,
      sampleCount: analysis.result.samples.length,
      missingSamples: 0,
    };
    provenance.model = analysis.result.model;
    provenance.limitations += ' ' + analysis.result.limitations;
  } else if (analysis?.kind === 'hf-skywave') {
    result = {
      kind: 'hf-skywave',
      status: analysis.estimate.scenario.compatible ? 'compatible geometry' : 'no compatible hop',
      distanceKm: analysis.estimate.scenario.outerRadiusKm,
      receivedDbm: null,
      marginDb: null,
      sampleCount: 0,
      missingSamples: 0,
    };
    provenance.model = 'ASE single-hop geometric scenario v1';
    provenance.limitations += ' ' + analysis.estimate.scenario.assumptions;
  }
  if (!analysis && mode === 'free-space') {
    let input = Object.fromEntries(
      Object.entries(draft.values).map(([key, value]) => [key, Number(value)]),
    ) as unknown as RfInputs;
    const target = draft.study === 'area' ? null : receiver;
    if (origin && target) input.distanceKm = measure([origin, target], 'distance').metres / 1000;
    if (draft.antenna?.enabled) {
      if (!origin || !target) throw new Error('Directional assumptions need both link sites.');
      input = directionalRfInputs(input, origin, target, draft.antenna);
    }
    const reference = calculateRf(input, parseRfEngineering(draft.engineering, 'free-space'));
    result = {
      kind: 'free-space',
      status: 'free-space reference',
      distanceKm: input.distanceKm,
      receivedDbm: reference.receivedDbm,
      marginDb: reference.marginDb - parseRfEngineering(draft.engineering, 'free-space').reserveDb,
      sampleCount: 0,
      missingSamples: 0,
    };
    provenance.model = 'ITU-R P.525 free-space equation / ASE v1';
  }
  if (draft.antenna?.enabled)
    provenance.limitations +=
      ' Includes a user-defined idealised horizontal parabolic antenna cut, not measured equipment data.';
  return parseRfStudy({
    ...(terrainEvidence ? { terrainEvidence } : {}),
    schemaVersion: 1,
    savedAt: new Date().toISOString(),
    draft,
    origin,
    receiver,
    siteNames,
    result,
    provenance,
  });
}
export function studyInputDifferences(baseline: RfStudySnapshot, current: RfDraft): string[] {
  return RF_FIELDS.filter(
    (field) => baseline.draft.values[field.key] !== current.values[field.key],
  ).map((field) => field.label);
}
