import { Alert } from '@/components/ui/Alert';

export function WebGlFallback() {
  return (
    <div className="flex h-full items-center justify-center p-6">
      <Alert tone="warning" title="WebGL2 is required" className="max-w-md">
        The globe needs WebGL2, which this browser or device does not provide. Enable hardware
        acceleration or use a current version of Chrome, Edge, Firefox or Safari.
      </Alert>
    </div>
  );
}
