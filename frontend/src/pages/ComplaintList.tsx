import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, ComplaintListItem } from '../api/client';

export default function ComplaintList() {
  const nav = useNavigate();
  const [items, setItems]   = useState<ComplaintListItem[]>([]);
  const [bank,  setBank]    = useState('');
  const [status, setStatus] = useState('');
  const [error, setError]   = useState<string | null>(null);

  useEffect(() => {
    api.listComplaints({ bank_code: bank || undefined, status: status || undefined, limit: 100 })
      .then(setItems)
      .catch(e => setError(String(e)));
  }, [bank, status]);

  if (error) return <div className="empty">Failed: {error}</div>;

  return (
    <>
      <div className="page-eyebrow">Browse</div>
      <h1 className="page-title">Complaints</h1>
      <p className="page-subtitle">
        All complaints received by the Reserve Bank, across banks and channels.
        Click any row to view full detail and forward to the bank.
      </p>

      <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
        <div className="field" style={{ width: 200 }}>
          <label>Bank</label>
          <select value={bank} onChange={e => setBank(e.target.value)}>
            <option value="">All banks</option>
            <option value="HDFC">HDFC</option>
            <option value="ICICI">ICICI</option>
            <option value="SBI">SBI</option>
            <option value="AXIS">AXIS</option>
            <option value="KOTAK">KOTAK</option>
          </select>
        </div>
        <div className="field" style={{ width: 240 }}>
          <label>Status</label>
          <select value={status} onChange={e => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="received">Received</option>
            <option value="forwarded_to_bank">Forwarded to Bank</option>
            <option value="bank_responded">Bank Responded</option>
            <option value="closed_satisfied">Closed Satisfied</option>
            <option value="escalated_to_io">Escalated to IO</option>
            <option value="deemed_rejected">Deemed Rejected</option>
          </select>
        </div>
      </div>

      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Reference</th>
              <th>Customer</th>
              <th>Bank</th>
              <th>Intent</th>
              <th>Channel</th>
              <th>Status</th>
              <th>Received</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={7} className="empty" style={{ padding: '40px 0' }}>
                No complaints match this filter.
              </td></tr>
            )}
            {items.map(c => (
              <tr key={c.id} onClick={() => nav(`/complaints/${c.id}`)}>
                <td><span className="ref-no">{c.reference_no}</span></td>
                <td>{c.customer_name}</td>
                <td>{c.bank_code}</td>
                <td style={{ textTransform: 'capitalize' }}>
                  {c.intent_class.replaceAll('_', ' ')}
                </td>
                <td className="muted" style={{ textTransform: 'capitalize' }}>
                  {c.language.toUpperCase()}
                </td>
                <td><span className={`badge ${c.status}`}>{c.status.replaceAll('_', ' ')}</span></td>
                <td className="mono">{new Date(c.received_at).toLocaleDateString('en-IN', {
                  day: '2-digit', month: 'short', year: 'numeric'
                })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
