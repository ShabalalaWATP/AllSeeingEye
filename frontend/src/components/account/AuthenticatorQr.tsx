import { useMemo } from 'react';
import QRCode from 'qrcode';

/** Encoded locally: provisioning secrets never go to a QR image service. */
export function AuthenticatorQr({ uri }: { uri: string }) {
  const matrix = useMemo(() => {
    try {
      return QRCode.create(uri, { errorCorrectionLevel: 'M' }).modules;
    } catch {
      return null;
    }
  }, [uri]);
  if (!matrix) return null;
  const cells: string[] = [];
  for (let row = 0; row < matrix.size; row++) {
    for (let column = 0; column < matrix.size; column++) {
      if (matrix.get(row, column)) cells.push(`M${column + 4} ${row + 4}h1v1h-1z`);
    }
  }
  return (
    <svg
      role="img"
      aria-label="Scan this QR code with your authenticator app"
      width={208}
      height={208}
      viewBox={`0 0 ${matrix.size + 8} ${matrix.size + 8}`}
      className="max-w-full rounded bg-white"
      shapeRendering="crispEdges"
    >
      <rect width="100%" height="100%" fill="white" />
      <path d={cells.join('')} fill="black" />
    </svg>
  );
}
