import type { calculateRf } from './rfPlanning';
import type { RfAnalysis } from './rfAnalysis';
import type { RfTerrainAnalysis } from './rfTerrainTypes';
import { hfGroundwaveReceiver, hfGroundwaveSummary } from './hfGroundwaveMap';
import { measure } from './measurements';

export interface RfResultExplanation {
  tone: 'pass' | 'caution' | 'blocked' | 'unknown' | 'scenario';
  headline: string;
  explanation: string;
  nextStep: string;
  limitations: string;
}
const FREE_SPACE_LIMITS =
  'Assumes an unobstructed path. Terrain, buildings, trees, interference and actual noise have not been assessed.';
const TERRAIN_LIMITS =
  'This is a sampled terrain screen, not measured coverage. Coarse ground heights can miss obstructions; buildings and trees are not measured. Interference, actual noise and changing weather have not been assessed.';
const GROUNDWAVE_LIMITS =
  'This groundwave model assumes uniform ground properties. Terrain, buildings, interference and actual noise can change reception. Check receiver sensitivity for the intended bandwidth and operating mode.';
const km = (distance: number) => distance.toLocaleString('en-GB', { maximumFractionDigits: 1 });

/** Explain threshold relationships without changing the physical calculation or its reserve. */
function powerExplanation(
  margin: number,
  planningMargin: number,
  limitations: string,
): RfResultExplanation {
  if (margin < 0)
    return {
      tone: 'caution',
      headline: 'Signal estimate is too weak for your receiver',
      explanation:
        'The estimated signal is weaker than the minimum signal level you entered for the receiver, even before your extra allowance is considered.',
      nextStep:
        'Check the receiver’s minimum signal setting for how you plan to use it, and check the antenna and cable settings. Review the distance between sites before changing equipment.',
      limitations,
    };
  if (planningMargin < 0)
    return {
      tone: 'caution',
      headline: 'Signal meets the receiver setting, but has too little spare strength',
      explanation:
        'The estimated signal reaches the minimum receiver setting, but falls short of the extra signal strength you asked to keep in reserve.',
      nextStep:
        'Review the equipment settings and why you chose the extra allowance. Do not remove it just to make the result pass.',
      limitations,
    };
  if (planningMargin === 0)
    return {
      tone: 'caution',
      headline: 'Signal only just meets your settings',
      explanation:
        'The estimated signal exactly meets the minimum receiver setting plus your chosen extra allowance. There is no spare strength beyond that allowance.',
      nextStep:
        'Check the assumptions and test the intended link. Actual noise or small changes may use up the spare signal strength.',
      limitations,
    };
  return {
    tone: 'pass',
    headline: 'Signal estimate meets your settings',
    explanation:
      'The estimated signal is stronger than the minimum receiver setting and includes the extra allowance you chose.',
    nextStep: 'Check the site conditions and receiver settings, then test the actual link.',
    limitations,
  };
}

export function freeSpaceExplanation(result: ReturnType<typeof calculateRf>): RfResultExplanation {
  if (result.beyondHorizon)
    return {
      tone: 'caution',
      headline: 'The path is beyond the assumed radio horizon',
      explanation:
        'At these antenna heights, the simple Earth-curvature check puts the receiver beyond the direct radio horizon. A strong signal estimate alone cannot establish a direct link.' +
        (result.marginDb < 0
          ? ' The signal estimate is also below the receiver’s minimum setting.'
          : ''),
      nextStep:
        'Use the terrain profile to review the path and consider another site or a feasible antenna height. Recheck the signal calculation after any change.',
      limitations: FREE_SPACE_LIMITS,
    };
  return powerExplanation(result.marginDb, result.planningMarginDb, FREE_SPACE_LIMITS);
}

function terrainLimitations(terrain: RfTerrainAnalysis): string {
  return (
    (terrain.belowSeaLevelSamples > 0
      ? 'Some source heights are below sea level and may describe the seabed rather than the water surface. Verify the ground and water levels before using the result. '
      : '') + TERRAIN_LIMITS
  );
}
function terrainAreaExplanation(terrain: RfTerrainAnalysis): RfResultExplanation {
  const passing = terrain.radials.filter((radial) => radial.clearDistanceKm > 0).length;
  const incomplete =
    terrain.missingSamples > 0 || terrain.radials.some((radial) => radial.status === 'unknown');
  const limitations =
    terrainLimitations(terrain) +
    ' Only the sampled directions were checked. Space between them and beyond the first failed or missing sample remains unassessed.';
  if (!terrain.radials.length || incomplete)
    return {
      tone: 'unknown',
      headline: 'There is not enough data to assess this area',
      explanation:
        passing > 0
          ? 'Some sampled paths passed, but missing terrain leaves other paths unassessed. Those gaps must not be treated as clear.'
          : 'The available terrain does not establish passing paths for this area. Missing or unassessed locations are not evidence of no reception.',
      nextStep:
        'Inspect the missing-data markers and choose the intended receiver site for a specific path check. Verify local ground heights where data is missing.',
      limitations,
    };
  if (!passing)
    return {
      tone: 'caution',
      headline: 'No checked path passed',
      explanation:
        'The first checked locations in every sampled direction failed a clearance or signal check. This does not establish that the whole surrounding area has no reception.',
      nextStep:
        'Place a receiver at the intended location and inspect its path and signal results before considering a different site or antenna height.',
      limitations,
    };
  const atLimit = terrain.radials.every(
    (radial) => radial.status === 'clear' && radial.clearDistanceKm >= terrain.maxDistanceKm,
  );
  return {
    tone: 'caution',
    headline: atLimit
      ? 'Checked paths passed out to the study limit'
      : 'Passing paths were found, but the study has limits',
    explanation: atLimit
      ? 'The checked paths met the chosen clearance and signal requirements through the sampled limit. That limit is not a maximum range, and it does not establish coverage between the paths.'
      : 'Some checked paths met the requirements for part of the study. Others stopped at an obstruction, restricted clearance or insufficient signal margin. The outline is not a continuous coverage boundary.',
    nextStep:
      'Check the intended receiver location directly. Use the sampled paths to guide that check rather than treating the shaded area as assured coverage.',
    limitations,
  };
}
function terrainExplanation(
  analysis: Extract<RfAnalysis, { kind: 'terrain' }>,
): RfResultExplanation {
  const terrain = analysis.terrain;
  if (terrain.kind === 'radial') return terrainAreaExplanation(terrain);
  const path = terrain.path;
  const limitations = terrainLimitations(terrain);
  if (
    !path ||
    path.status === 'unknown' ||
    terrain.missingSamples > 0 ||
    path.marginDb === null ||
    path.planningMarginDb === null ||
    path.minimumLosClearanceM === null ||
    path.minimumFresnelClearanceM === null
  )
    return {
      tone: 'unknown',
      headline: 'There is not enough data to assess this path',
      explanation:
        'Terrain or calculation results are missing. The path has not passed a clearance or signal check; an empty result does not mean the path is clear.',
      nextStep:
        'Inspect the missing samples and confirm the two sites. Try the analysis again or verify the missing ground heights from another appropriate source.',
      limitations,
    };
  if (path.status === 'blocked' || path.minimumLosClearanceM <= 0)
    return {
      tone: 'blocked',
      headline: 'The direct radio path is obstructed',
      explanation:
        'The sampled ground or assumed obstacles cross the direct radio path. A strong power result does not remove that obstruction, and an obstructed direct path does not mean zero reception.',
      nextStep:
        'Inspect the marked obstruction in the profile. Consider a different site or a feasible antenna height, then run the analysis again.',
      limitations,
    };
  const planningMargin = path.planningMarginDb ?? path.marginDb - (path.reserveDb ?? 0);
  if (path.marginDb < 0 || planningMargin < 0) {
    const power = powerExplanation(path.marginDb, planningMargin, limitations);
    if (path.minimumFresnelClearanceM < 0) {
      power.explanation += ' The clearance needed around the direct path is also restricted.';
      power.nextStep =
        'Review both the restricted clearance in the profile and the equipment inputs. Fixing signal margin alone will not clear the path.';
    }
    return power;
  }
  if (path.minimumFresnelClearanceM < 0)
    return {
      tone: 'caution',
      headline: 'The direct path is clear, but there is too little space around it',
      explanation:
        'Radio waves need space around the direct path, called the Fresnel zone. The checked ground heights or assumed obstacles intrude into that space, even though they do not cross the direct line.',
      nextStep:
        'Inspect the restricted section of the profile. Consider another site or a feasible antenna height, then check the full path again.',
      limitations,
    };
  if (terrain.belowSeaLevelSamples > 0)
    return {
      tone: 'caution',
      headline: 'The ground and water levels need checking',
      explanation:
        'The numerical path checks passed, but some source heights are below sea level. The model may have used seabed heights where the actual radio path crosses water.',
      nextStep:
        'Confirm whether these samples represent land or water before relying on the clearance result.',
      limitations,
    };
  if (path.status === 'risk')
    return {
      tone: 'caution',
      headline: 'The checked path needs further review',
      explanation:
        'The analysis flags a risk. A strong signal estimate alone is not enough to treat the full path as clear.',
      nextStep:
        'Review the path profile, space around the path and your extra signal allowance together.',
      limitations,
    };
  const power = powerExplanation(path.marginDb, planningMargin, limitations);
  power.explanation =
    'The checked ground heights and assumed obstacles leave enough space around the path. ' +
    power.explanation;
  return power;
}

function groundwaveExplanation(
  analysis: Extract<RfAnalysis, { kind: 'hf-groundwave' }>,
): RfResultExplanation {
  const reserve = analysis.engineering?.reserveDb ?? 0;
  const summary = hfGroundwaveSummary(analysis.result, analysis.input.sensitivityDbm, reserve);
  if (analysis.receiver) {
    const distance = measure([analysis.origin, analysis.receiver], 'distance').metres / 1000;
    const receiver = hfGroundwaveReceiver(analysis.result, distance);
    if (!receiver)
      return {
        tone: 'unknown',
        headline: 'This receiver is outside the checked distance range',
        explanation: `The model checks ${km(summary.checkedFromKm)} to ${km(summary.checkedToKm)} km. It provides no signal estimate at this receiver, even if other checked distances pass.`,
        nextStep:
          'Confirm the site coordinates and use a model that supports this separation. Do not extend the plotted curve beyond its checked interval.',
        limitations: GROUNDWAVE_LIMITS,
      };
    const margin = receiver.receivedDbm - analysis.input.sensitivityDbm;
    const explanation = powerExplanation(margin, margin - reserve, GROUNDWAVE_LIMITS);
    explanation.explanation =
      (receiver.interpolated
        ? 'At this receiver, the signal is estimated between neighbouring model samples. '
        : 'This receiver matches a checked model distance. ') + explanation.explanation;
    return explanation;
  }
  if (summary.noPassing)
    return {
      tone: 'caution',
      headline: 'No passing range starts at the first checked distance',
      explanation: `The first checked distance, ${km(summary.checkedFromKm)} km, falls below your minimum receiver setting plus the extra allowance. Closer distances are unassessed; any later isolated passing samples do not establish a consecutive passing range.`,
      nextStep:
        'Check the assumed ground properties and receiver sensitivity. Place a receiver to examine a particular supported separation.',
      limitations: GROUNDWAVE_LIMITS,
    };
  if (summary.atLimit)
    return {
      tone: 'caution',
      headline: 'Signal meets your settings out to the checked limit',
      explanation: `Every checked distance meets your minimum receiver setting plus the extra allowance through ${km(summary.checkedToKm)} km. This is the search limit, not an established maximum range or proof of coverage at every location.`,
      nextStep:
        'Place the intended receiver and review its result, ground assumptions and actual operating conditions.',
      limitations: GROUNDWAVE_LIMITS,
    };
  return {
    tone: 'caution',
    headline: 'Signal drops below your settings between checked distances',
    explanation: `Consecutive checked distances meet your minimum receiver setting plus the extra allowance through ${km(summary.radiusKm ?? summary.checkedFromKm)} km. The next checked distance, ${km(summary.firstFailureKm ?? summary.checkedToKm)} km, falls below it. The precise transition is unresolved; later isolated passing samples do not extend this bound.`,
    nextStep:
      'Inspect the intended receiver location within the sampled interval. Confirm the assumed ground properties and equipment settings before using the range as a planning guide.',
    limitations: GROUNDWAVE_LIMITS,
  };
}
export function analysisExplanation(analysis: RfAnalysis): RfResultExplanation {
  if (analysis.kind === 'terrain') return terrainExplanation(analysis);
  if (analysis.kind === 'hf-groundwave') return groundwaveExplanation(analysis);
  return {
    tone: 'scenario',
    headline: analysis.estimate.scenario.compatible
      ? 'This shows travel distances only'
      : 'No travel distance fits these settings',
    explanation: analysis.estimate.scenario.compatible
      ? 'The rings show where radio waves could return to the ground using your assumptions about an atmospheric layer and departure angles. They do not estimate signal strength.'
      : 'The chosen frequency and assumptions about the atmospheric layer and departure angles do not give a path returning to the ground after one hop. Other paths or different conditions may still be possible.',
    nextStep:
      'Check the assumed atmospheric conditions. Use a suitable radio model and link checks if you need to assess reception.',
    limitations:
      'No current atmospheric readings or signal-strength calculation. Absorption, noise and interference are not modelled. Transmit power and mast height do not determine these rings.',
  };
}
