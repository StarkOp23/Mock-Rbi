import { useEffect, useState } from 'react';
import { api, DashboardStats } from '../api/client';

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboardStats()
      .then(setStats)
      .catch(e => setError(String(e)));
  }, []);

  if (error) return <div className="empty">Failed to load: {error}</div>;
  if (!stats) return <div className="empty">Loading…</div>;

  const tiles = [
    { eyebrow: 'Total Complaints',   value: stats.total_complaints,
      foot: 'Across all banks, all time' },
    { eyebrow: 'Open / In Progress', value: stats.open_count,
      foot: 'Awaiting bank action' },
    { eyebrow: 'Average TAT (days)', value: stats.avg_tat_days?.toFixed(1) ?? '—',
      foot: 'Of resolved cases' },
    { eyebrow: 'SLA Breaches',       value: stats.breach_count,
      foot: 'Cases breaching 30-day window' },
  ];

  return (
    <>
      <div className="page-eyebrow">RBI CMS</div>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">
        Real-time view of customer complaints lodged with the Reserve Bank under
        the Integrated Ombudsman Scheme 2021. Demo dataset; no production traffic.
      </p>

      <div className="tile-grid">
        {tiles.map(t => (
          <div className="tile" key={t.eyebrow}>
            <div className="tile-eyebrow">{t.eyebrow}</div>
            <div className="tile-value">{t.value}</div>
            <div className="tile-foot">{t.foot}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <DistributionCard title="By Bank"   data={stats.by_bank} />
        <DistributionCard title="By Status" data={stats.by_status} />
      </div>

      <div style={{ marginTop: 24 }}>
        <DistributionCard title="By Intent Class" data={stats.by_intent} />
      </div>
    </>
  );
}

function DistributionCard({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const total   = entries.reduce((s, [, v]) => s + v, 0) || 1;
  return (
    <div className="detail-card">
      <h3 className="section">{title}</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {entries.length === 0 && <div className="muted">No data yet.</div>}
        {entries.map(([k, v]) => {
          const pct = (v / total) * 100;
          return (
            <div key={k}>
              <div style={{ display: 'flex', justifyContent: 'space-between',
                            fontSize: 12, marginBottom: 4 }}>
                <span style={{ textTransform: 'capitalize' }}>{k.replaceAll('_', ' ')}</span>
                <span className="mono">{v}</span>
              </div>
              <div style={{ height: 4, background: 'var(--rbi-grey-line)' }}>
                <div style={{ width: `${pct}%`, height: '100%',
                              background: 'var(--rbi-navy)' }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
