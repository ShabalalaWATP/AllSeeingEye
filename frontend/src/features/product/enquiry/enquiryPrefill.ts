/**
 * Hands a cost estimate from the Deploy chapter to the enquiry form's message. The
 * channel lives only in the mounted story: nothing is stored, sent or submitted, and
 * text the visitor has already typed is never replaced.
 */
import { createContext, useContext, useEffect } from 'react';

export const MESSAGE_LIMIT = 2000;

export type PrefillOutcome = 'filled' | 'appended' | 'unchanged' | 'too_long';

export interface EnquiryPrefill {
  /** Whether an enquiry form is on the page to receive an estimate. */
  available: boolean;
  /** Offer text to the mounted form, if there is one. */
  offer: (text: string) => void;
  /** Register the form as the receiver; returns the unregister function. */
  receive: (receiver: (text: string) => void) => () => void;
}

export function createPrefillChannel(): Omit<EnquiryPrefill, 'available'> {
  let receiver: ((text: string) => void) | null = null;
  return {
    offer: (text) => receiver?.(text),
    receive: (next) => {
      receiver = next;
      return () => {
        if (receiver === next) receiver = null;
      };
    },
  };
}

const UNAVAILABLE: EnquiryPrefill = {
  available: false,
  offer: () => undefined,
  receive: () => () => undefined,
};

export const EnquiryPrefillContext = createContext<EnquiryPrefill>(UNAVAILABLE);

export function useEnquiryPrefill(): EnquiryPrefill {
  return useContext(EnquiryPrefillContext);
}

/** Registers `receiver` for as long as the calling form is mounted. */
export function useEnquiryPrefillReceiver(receiver: (text: string) => void): void {
  const { receive } = useEnquiryPrefill();
  useEffect(() => receive(receiver), [receive, receiver]);
}

/**
 * Puts `text` into an empty message, or below what the visitor has written when it
 * fits. A message that already holds the text, or has no room, is left as it is.
 */
export function mergePrefill(
  message: string,
  text: string,
  limit = MESSAGE_LIMIT,
): { message: string; outcome: PrefillOutcome } {
  if (message.trim() === '') return { message: text.slice(0, limit), outcome: 'filled' };
  if (message.includes(text)) return { message, outcome: 'unchanged' };
  const combined = `${message.trimEnd()}\n\n${text}`;
  if (combined.length > limit) return { message, outcome: 'too_long' };
  return { message: combined, outcome: 'appended' };
}

export const PREFILL_NOTICES: Record<PrefillOutcome, string> = {
  filled: 'The estimate is now in your message. Edit it as you wish; nothing has been sent.',
  appended: 'The estimate has been added below your message. Nothing has been sent.',
  unchanged: 'This estimate is already in your message.',
  too_long: 'Your message has no room for the estimate. Shorten it, then send the estimate again.',
};
