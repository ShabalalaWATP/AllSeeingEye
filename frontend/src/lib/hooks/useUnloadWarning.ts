import { useEffect, type RefObject } from 'react';

/**
 * In-memory drafts cannot survive a reload or a closed tab, so the browser asks first while a
 * form holds unsent work. `released` turns the warning off once the work has been accepted.
 */
export function useUnloadWarning(dirty: boolean, released?: RefObject<boolean>) {
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      if (released?.current !== true) event.preventDefault();
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty, released]);
}
