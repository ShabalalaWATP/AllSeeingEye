import { expect, it } from 'vitest';
import { recordScopeError } from './recordScope';

it.each([
  ['WB:GB:NY.GDP.MKTP.CD:2024:2020', 'GB'],
  ['WB:GB:NY.GDP.MKTP.CD:1900:1920', 'GB'],
  ['WB:GB:NY.GDP.MKTP.CD:2020:2024:extra', 'GB'],
  ['WB:GB:NY.GDP.MKTP.CD:2020:2024', 'IR'],
  ['parliament:', 'CN'],
  ['academic:', 'GB'],
  ['ooni:IR', 'GB'],
  ['ooni:invalid', ''],
])('rejects invalid or incompatible specialist scope %s / %s', (subject, country) => {
  expect(recordScopeError(subject, country)).not.toBeNull();
});
it.each([
  ['WB:gb:NY.GDP.MKTP.CD:2020:2024', 'GB'],
  ['parliament:', 'GB'],
  ['academic:', ''],
  ['ooni:ir', 'IR'],
  ['', 'IR'],
])('accepts valid specialist scope %s / %s', (subject, country) => {
  expect(recordScopeError(subject, country)).toBeNull();
});
