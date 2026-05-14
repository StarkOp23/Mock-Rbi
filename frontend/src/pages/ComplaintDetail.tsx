import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, ComplaintDetail as TDetail } from '../api/client';
import { useToast } from '../App';

export default function ComplaintDetail() {
  const { id }   = useParams<{ id: string }>();
  const nav      = useNavigate();
  const { push } = useToast();
  const [data, setData] = useState<TDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!id) return;
    try {
      setData(await api.getComplaint(id));
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [id]);

  async function forward() {
    if (!data) return;
    setBusy(true);
    try {
      const res = await api.forwardToBank(data.complaint.id);
      if (res.success) {
        push(`Forwarded to ${res.bank_code}; bank run ${res.bank_run_id ?? '—'}`);
      } else {
        push(`Forwarding failed: ${res.detail}`, 'error');
      }
      await refresh();
    } catch (e) {
      push(`Error: ${e}`, 'error');
    } finally {
      setBusy(false);
    }
  }

  if (error)     return <div className="empty">Failed: {error}</div>;
  if (!data)     return <div className="empty">Loading…</div>;

  const c = data.complaint;
  const canForward = c.status === 'received';

  return (
    <>
      <div className="page-eyebrow">Complaint</div>
      <h1 className="page-title">
        <span className="ref-no" style={{ fontSize: 28 }}>{c.reference_no}</span>
      </h1>
      <p className="page-subtitle">
        Status: <span className={`badge ${c.status}`} style={{ marginLeft: 8 }}>
          {c.status.replaceAll('_', ' ')}
        </span>
      </p>

      <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
        <button className="btn gold" onClick={forward}
                disabled={busy || !canForward}>
          {busy ? 'Forwarding…' : canForward ? '→ Forward to Bank' : 'Already Forwarded'}
        </button>
        <button className="btn ghost" onClick={() => nav('/complaints')}>← Back to List</button>
      </div>

      <div className="detail-grid">
        <div>
          <div className="detail-card">
            <h3 className="section">Customer</h3>
            <dl className="kv">
              <dt>Name</dt>     <dd>{c.customer_name}</dd>
              <dt>CBS Token</dt><dd className="mono">{c.customer_token_id}</dd>
              <dt>Email</dt>    <dd>{c.customer_email ?? '—'}</dd>
              <dt>Mobile</dt>   <dd className="mono">{c.customer_mobile ?? '—'}</dd>
              <dt>Language</dt> <dd>{c.language.toUpperCase()}</dd>
            </dl>
          </div>

          <div className="detail-card">
            <h3 className="section">Routing</h3>
            <dl className="kv">
              <dt>Bank</dt>     <dd>{c.bank_code}</dd>
              <dt>Channel</dt>  <dd style={{ textTransform: 'capitalize' }}>
                                  {c.channel.replaceAll('_', ' ')}</dd>
              <dt>Intent</dt>   <dd style={{ textTransform: 'capitalize' }}>
                                  {c.intent_class.replaceAll('_', ' ')}</dd>
              <dt>Received</dt> <dd className="mono">
                                  {new Date(c.received_at).toLocaleString('en-IN')}</dd>
              {c.closed_at && (<>
                <dt>Closed</dt> <dd className="mono">
                                  {new Date(c.closed_at).toLocaleString('en-IN')}</dd>
              </>)}
            </dl>
          </div>
        </div>

        <div>
          <div className="detail-card">
            <h3 className="section">Customer's Words</h3>
            <div className="complaint-text">{c.raw_text}</div>
          </div>

          {data.forwardings.length > 0 && (
            <div className="detail-card">
              <h3 className="section">Forwarding History</h3>
              <div className="timeline">
                {data.forwardings.map(f => (
                  <div className="timeline-event" key={f.id}>
                    <div className="timeline-time">
                      {new Date(f.forwarded_at).toLocaleString('en-IN')}
                    </div>
                    <div>
                      Forwarded to <strong>{f.bank_code}</strong> — HTTP&nbsp;
                      <span className="mono">{f.http_status ?? '—'}</span>
                      {f.bank_run_id && <> · run <span className="mono">{f.bank_run_id}</span></>}
                      {f.error_message && <div style={{ color: 'var(--status-breach)',
                                                        fontSize: 12, marginTop: 4 }}>
                        {f.error_message}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.responses.length > 0 && (
            <div className="detail-card">
              <h3 className="section">Bank Responses</h3>
              {data.responses.map(r => (
                <div key={r.id} style={{ marginBottom: 24, paddingBottom: 16,
                                         borderBottom: '1px solid var(--rbi-grey-line)' }}>
                  <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                    <span className={`badge ${r.outcome}`}>{r.outcome.replaceAll('_', ' ')}</span>
                    {r.breached_30_day && <span className="badge deemed_rejected">SLA Breach</span>}
                  </div>
                  <dl className="kv">
                    <dt>From Bank</dt>     <dd>{r.bank_code}</dd>
                    <dt>Received</dt>      <dd className="mono">
                                              {new Date(r.received_at).toLocaleString('en-IN')}</dd>
                    <dt>TAT</dt>           <dd>{r.tat_days} days</dd>
                    <dt>Compensation</dt>  <dd className="mono">
                                              ₹ {r.compensation_inr.toLocaleString('en-IN')}</dd>
                    <dt>Bank Run ID</dt>   <dd className="mono">{r.bank_run_id ?? '—'}</dd>
                  </dl>
                  {r.customer_letter && (
                    <details style={{ marginTop: 12 }}>
                      <summary style={{ cursor: 'pointer', fontSize: 12,
                                        color: 'var(--rbi-navy)', letterSpacing: '0.1em',
                                        textTransform: 'uppercase' }}>
                        View Customer Letter
                      </summary>
                      <div className="complaint-text"
                           style={{ marginTop: 12, whiteSpace: 'pre-wrap',
                                    fontFamily: 'var(--font-body)', fontSize: 13 }}>
                        {r.customer_letter}
                      </div>
                    </details>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
