/** Reviewed text only. Null operator decisions remain visible and block publication. */
import notice from './privacy.json';
import declaredStorage from './storage.json';
import service from './service.json';
import terms from './terms.json';
import acceptableUse from './acceptable-use.json';
import accessibility from './accessibility.json';
import publicationApproved from 'virtual:policy-approval';

interface Purpose {
  name: string;
  data: string;
  purpose: string;
  lawfulBasis: string | null;
}

export interface PrivacyNotice {
  version: string;
  scope: string;
  operator: Record<string, string | null>;
  purposes: Purpose[];
  retention: { name: string; behaviour: string }[];
  requestProcedure: { contact: string; approvedOn: string; source: string; steps: string[] };
  rights: string;
  objection: string;
  publicSources: string;
  externalMedia: string;
  references: { label: string; url: string }[];
}

export interface StorageDeclaration {
  name: string;
  kind: string;
  purpose: string;
  contents: string;
  duration: string;
  sources: string[];
}

/** Published wording, or a decision the operator has not made. Pending items block publication. */
export type PolicyWording = string | { pending: string };

export interface PolicyDocumentSection {
  id: string;
  title: string;
  paragraphs: PolicyWording[];
  items?: PolicyWording[];
}

export interface PolicyDocument {
  sections: PolicyDocumentSection[];
}

export const privacyNotice: PrivacyNotice = notice;
export const storageDeclaration: readonly StorageDeclaration[] = declaredStorage;
export const noticeApproved = publicationApproved;
export const serviceDetails: {
  businessDisclosure: string | null;
  businessAddress: string | null;
  accessibilityContact: string | null;
} = service;
/** The version date must match `CURRENT_TERMS_VERSION` in the backend's `domain/terms.py`. */
export const termsDocument: PolicyDocument & { version: string } = terms;
export const acceptableUseDocument: PolicyDocument = acceptableUse;
export const accessibilityStatement: PolicyDocument & { lastReviewed: string; nextReview: string } =
  accessibility;
