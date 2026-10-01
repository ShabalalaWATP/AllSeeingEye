import { useContext, useEffect, type RefObject } from 'react';
import { UNSAFE_DataRouterContext, useBlocker, type BlockerFunction } from 'react-router';

import { useUnloadWarning } from '@/lib/hooks/useUnloadWarning';

interface LeaveGuardProps {
  /** In-app navigation would discard work that the form cannot restore. */
  unrestorable: boolean;
  /** Any unsent work, which a reload or closed tab always discards. */
  dirty: boolean;
  message: string;
  /** Set once the form's work has been accepted, so its own navigation is never blocked. */
  released?: RefObject<boolean>;
}

function Guard({ unrestorable, dirty, message, released }: LeaveGuardProps) {
  const shouldBlock: BlockerFunction = ({ currentLocation, nextLocation }) =>
    unrestorable &&
    released?.current !== true &&
    (currentLocation.pathname !== nextLocation.pathname ||
      currentLocation.search !== nextLocation.search);
  const blocker = useBlocker(shouldBlock);
  useEffect(() => {
    if (blocker.state !== 'blocked') return;
    // The browser's own confirmation is modal, focus-managed and keyboard operable.
    if (window.confirm(message)) blocker.proceed();
    else blocker.reset();
  }, [blocker, message]);
  useUnloadWarning(dirty, released);
  return null;
}

/**
 * Asks before leaving a form whose unsent work would be lost. Drafts kept in memory survive
 * in-app navigation, so only unrestorable work blocks it; a reload loses every draft. Outside
 * a data router (some isolated tests) there is nothing to block.
 */
export function LeaveGuard(props: LeaveGuardProps) {
  return useContext(UNSAFE_DataRouterContext) ? <Guard {...props} /> : null;
}
