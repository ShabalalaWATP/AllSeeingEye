import { BrandMark } from '@/components/brand/BrandMark';

export interface LoadingScreenProps {
  label?: string;
}

/** Full-area waiting state shown while the session is checked or a bundle loads. */
export function LoadingScreen({ label = 'Loading' }: LoadingScreenProps) {
  return (
    <div
      role="status"
      className="flex h-full min-h-64 w-full flex-col items-center justify-center gap-4 bg-ground"
    >
      <BrandMark size={56} />
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">{label}</p>
    </div>
  );
}
