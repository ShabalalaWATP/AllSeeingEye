/** Reviewed text only. Null operator decisions remain visible and block publication. */
import notice from './privacy.json';
import declaredStorage from './storage.json';
import service from './service.json';
import publicationApproved from 'virtual:policy-approval';

interface Purpose {
  name: string;
  data: string;
  purpose: string;
  lawfulBasis: string | null;
}

export interface PrivacyNotice {
  version: string;
  operator: Record<string, string | null>;
  purposes: Purpose[];
  retention: { name: string; behaviour: string }[];
  requestProcedure: { contact: string; approvedOn: string; source: string; steps: string[] };
  rights: string;
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

export const privacyNotice: PrivacyNotice = notice;
export const storageDeclaration: readonly StorageDeclaration[] = declaredStorage;
export const noticeApproved = publicationApproved;
export const serviceDetails: {
  terms: string | null;
  businessDisclosure: string | null;
  accessibilityContact: string | null;
} = service;
