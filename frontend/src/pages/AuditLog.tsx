import { useEffect, useState } from 'react';
import { api, AuditEvent } from '../api/client';

export default function AuditLog() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError]   = useState<string | null>(null);

  useEffect(() => {
    api.audit({ limit: 200 })
      .then(setEvents)
      .catch(e => setError(String(e)));
  }, []);

  if (error) return <div className="empty">Failed: {error}</div>;

  return (
    <>
      <div className="page-eyebrow">Compliance</div>
      <h1 className="page-title">Audit Log</h1>
      <p className="page-subtitle">
        Append-only ledger of every action taken in the RBI CMS Portal. Mirrors
        the audit pattern used inside the Crest platform.
      </p>

      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>When</th>
              <th>Actor</th>
              <th>Event</th>
              <th>Resource</th>
              <th>Outcome</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 && (
              <tr><td colSpan={6} className="empty" style={{ padding: '40px 0' }}>
                No events yet.
              </td></tr>
            )}
            {events.map(e => (
              <tr key={e.id}>
                <td className="mono">{new Date(e.occurred_at).toLocaleString('en-IN')}</td>
                <td>{e.actor}</td>
                <td><span className="mono">{e.event_type}</span></td>
                <td className="mono">{e.resource_id ?? '—'}</td>
                <td>
                  <span className={`badge ${e.outcome === 'success' ? 'bank_responded' : 'deemed_rejected'}`}>
                    {e.outcome}
                  </span>
                </td>
                <td>
                  <details>
                    <summary style={{ cursor: 'pointer', fontSize: 11,
                                      color: 'var(--rbi-navy)',
                                      textTransform: 'uppercase',
                                      letterSpacing: '0.1em' }}>JSON</summary>
                    <pre className="mono" style={{ background: 'var(--rbi-cream)',
                                                   padding: 8, marginTop: 6,
                                                   fontSize: 11, maxWidth: 360,
                                                   overflow: 'auto' }}>
{JSON.stringify(e.detail, null, 2)}</pre>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
