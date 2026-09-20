import { useEffect, useState } from 'react';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';

const initialVisibility = {
  measurement: true,
  sketch: true,
  research: true,
  radio: true,
  route: true,
  terrain: true,
};
export type WorkspaceOverlay = keyof typeof initialVisibility;

/** Visibility never removes an artefact or changes the inputs to its analysis. */
export function useWorkspaceVisibility() {
  const [visible, setVisibility] = useState(initialVisibility);
  useEffect(() => {
    const clear = () => setVisibility(initialVisibility);
    const offAccess = subscribeWorkspaceAccess(clear);
    const offUser = useAuthStore.subscribe((next, previous) => {
      if (
        next.user?.id !== previous.user?.id ||
        next.status !== previous.status ||
        next.user?.role !== previous.user?.role ||
        next.user?.is_active !== previous.user?.is_active
      )
        clear();
    });
    return () => {
      offAccess();
      offUser();
    };
  }, []);
  return {
    visible,
    setVisible: (key: WorkspaceOverlay, value: boolean) =>
      setVisibility((previous) => ({ ...previous, [key]: value })),
  };
}
