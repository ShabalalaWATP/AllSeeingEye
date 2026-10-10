import * as z from 'zod/mini';

import type { EnterpriseEnquiryInput } from '@/lib/api/enterpriseEnquiries';

// Draft-only choices include an empty selection. The transmitted DTO is generated.
export type EnquiryDraft = {
  [K in keyof EnterpriseEnquiryInput]: EnterpriseEnquiryInput[K] | '';
} & { privacyRead: boolean };
export type EnquiryErrors = Partial<Record<keyof EnquiryDraft, string>>;

export const EMPTY_ENQUIRY: EnquiryDraft = {
  name: '',
  email: '',
  organisation: '',
  role: '',
  deployment_interest: '',
  expected_users: '',
  message: '',
  website: '',
  privacyRead: false,
};

export const DEPLOYMENTS = [
  { value: '', label: 'Choose a deployment option' },
  { value: 'own_cloud', label: 'Own cloud' },
  { value: 'on_premises', label: 'On-premises' },
  { value: 'air_gapped', label: 'Air-gapped' },
  { value: 'undecided', label: 'Not sure yet' },
] as const satisfies readonly { value: EnquiryDraft['deployment_interest']; label: string }[];
export const USER_COUNTS = [
  { value: '', label: 'Choose an expected number of users' },
  { value: '1_10', label: '1 to 10' },
  { value: '11_50', label: '11 to 50' },
  { value: '51_250', label: '51 to 250' },
  { value: '250_plus', label: 'More than 250' },
] as const satisfies readonly { value: EnquiryDraft['expected_users']; label: string }[];

export const FIELD_MESSAGES: Record<keyof EnterpriseEnquiryInput, string> = {
  name: 'Enter your name (up to 100 characters).',
  email: 'Enter a valid work email address (up to 254 characters).',
  organisation: 'Enter your organisation (up to 150 characters).',
  role: 'Use up to 100 characters for your role.',
  deployment_interest: 'Choose a deployment option.',
  expected_users: 'Choose the expected number of users.',
  message: 'Use up to 2,000 characters for your message.',
  website: 'Please reload the page and try again.',
};

const schema: z.ZodMiniType<EnterpriseEnquiryInput> = z.object({
  name: z.string().check(z.trim(), z.minLength(1), z.maxLength(100)),
  // A permissive format check leaves final address validation to the API.
  email: z.string().check(z.trim(), z.maxLength(254), z.regex(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)),
  organisation: z.string().check(z.trim(), z.minLength(1), z.maxLength(150)),
  role: z.string().check(z.trim(), z.maxLength(100)),
  deployment_interest: z.enum(['own_cloud', 'on_premises', 'air_gapped', 'undecided']),
  expected_users: z.enum(['1_10', '11_50', '51_250', '250_plus']),
  message: z.string().check(z.trim(), z.maxLength(2000)),
  website: z.string().check(z.maxLength(200)),
});

export function validateEnquiry(draft: EnquiryDraft) {
  const { privacyRead, ...input } = draft;
  const result = schema.safeParse(input);
  const errors: EnquiryErrors = {};
  if (!result.success) {
    for (const issue of result.error.issues) {
      const field = issue.path[0];
      if (typeof field === 'string' && Object.hasOwn(FIELD_MESSAGES, field)) {
        const key = field as keyof EnterpriseEnquiryInput;
        errors[key] = FIELD_MESSAGES[key];
      }
    }
  }
  if (!privacyRead) errors.privacyRead = 'Confirm that you have read the privacy notice.';
  return { errors, input: result.success && privacyRead ? result.data : null };
}
