import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, ComplaintListItem } from '../api/client';

export default function BankInbox() {
  const nav = useNavigate();
  const [items, setItems] = useState<ComplaintListItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listComplaints({ status: 'bank_responded', limit: 100 })
      .then(setItems)
      .catch(e => setError(String(e)));
  }, []);

  if (error) return <div className="empty">Failed: {error}</div>;

  return (
    <>
      <div className="page-eyebrow">Resolutions</div>
      <h1 className="page-title">Bank Responses</h1>
      <p className="page-subtitle">
        Complaints for which banks have submitted a final resolution. Click to
        review the bank's disposition and customer letter.
      </p>

      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Reference</th>
              <th>Customer</th>
              <th>Bank</th>
              <th>Intent</th>
              <th>Received</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={5} className="empty" style={{ padding: '40px 0' }}>
                No bank responses yet. Forward a complaint and have the bank's
                Crest agent post back to <span className="mono">/api/v1/responses</span>.
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
