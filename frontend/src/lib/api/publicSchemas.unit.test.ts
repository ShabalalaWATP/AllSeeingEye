import { expect, it } from 'vitest';

import { errorEnvelopeSchema } from './errorEnvelope';
import { siteFactsSchema } from './site';

it('retains conservative public defaults and strips undeclared installation data', () => {
  expect(siteFactsSchema.parse({ product_page_enabled: false, private: 'not public' })).toEqual({
    product_page_enabled: false,
    enterprise_enquiries_enabled: false,
    enterprise_enquiry_retention_days: 365,
  });
});

it.each([
  null,
  {},
  { product_page_enabled: 'true' },
  { product_page_enabled: true, enterprise_enquiries_enabled: 1 },
])('rejects invalid public feature flags: %j', (value) => {
  expect(siteFactsSchema.safeParse(value).success).toBe(false);
});

it.each([29, 3651, 30.5, '365', null])('rejects an invalid retention value: %j', (days) => {
  expect(
    siteFactsSchema.safeParse({
      product_page_enabled: true,
      enterprise_enquiry_retention_days: days,
    }).success,
  ).toBe(false);
});

it.each([30, 3650])('accepts the retention boundary %i', (days) => {
  expect(
    siteFactsSchema.parse({ product_page_enabled: true, enterprise_enquiry_retention_days: days })
      .enterprise_enquiry_retention_days,
  ).toBe(days);
});

it('retains transport error validation, including bounded request IDs and string field messages', () => {
  const error = {
    code: 'invalid_request',
    message: 'Invalid input',
    request_id: 'abcd-1234',
    fields: { email: 'Invalid email' },
  };
  expect(errorEnvelopeSchema.parse({ error })).toEqual({ error });
  for (const invalid of [
    { ...error, request_id: 'short' },
    { ...error, request_id: '<script>bad' },
    { ...error, request_id: 'x'.repeat(65) },
    { ...error, fields: { email: 1 } },
    { ...error, code: null },
  ])
    expect(errorEnvelopeSchema.safeParse({ error: invalid }).success).toBe(false);
  expect(errorEnvelopeSchema.parse({ error: { code: 'failure', message: 'Try again' } })).toEqual({
    error: { code: 'failure', message: 'Try again' },
  });
});
