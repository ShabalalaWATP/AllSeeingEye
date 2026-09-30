import type { CyberItem } from '@/lib/api/cyber';

export function KevScores({ kev }: { kev: NonNullable<CyberItem['kev']> }) {
  return (
    <div className="mt-3 space-y-1 text-xs text-muted">
      <p>
        {kev.epss
          ? `FIRST EPSS probability model: ${(kev.epss.probability * 100).toFixed(2)}%, percentile ${(kev.epss.percentile * 100).toFixed(2)} (${kev.epss.date}).`
          : 'FIRST EPSS: unavailable.'}
      </p>
      <p>
        {kev.cvss
          ? `CVSS ${kev.cvss.version} base severity: ${kev.cvss.base_score}/10. Source: ${kev.cvss.source}; NVD record updated ${kev.cvss.updated_at}.`
          : 'NVD CVSS: unavailable.'}
      </p>
      {kev.cvss && <p className="break-all font-mono">{kev.cvss.vector}</p>}
      <p>
        EPSS estimates exploitation in the next 30 days; CVSS describes severity. CISA already lists
        this vulnerability as known exploited.
      </p>
    </div>
  );
}
