import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../App';

const INTENT_CLASSES = [
  'deficiency_in_service', 'atm_card', 'mobile_internet_banking',
  'mis_selling', 'loan_advances', 'pension', 'levy_of_charges',
  'cheque_collection', 'deceased_claim', 'other',
];

const CHANNELS = [
  'cms_portal_web', 'email', 'physical_mail', 'call_center',
];

const LANGUAGES = [
  ['en', 'English'], ['hi', 'Hindi'], ['mr', 'Marathi'], ['ta', 'Tamil'],
  ['te', 'Telugu'],  ['kn', 'Kannada'], ['bn', 'Bengali'], ['gu', 'Gujarati'],
  ['pa', 'Punjabi'], ['ml', 'Malayalam'],
];

export default function ComplaintIntake() {
  const nav = useNavigate();
  const { push } = useToast();
  const [busy, setBusy] = useState(false);

  const [form, setForm] = useState({
    customer_name:     '',
    customer_email:    '',
    customer_mobile:   '',
    customer_token_id: '',
    bank_code:         'HDFC',
    channel:           'cms_portal_web',
    intent_class:      'atm_card',
    language:          'en',
    raw_text:          '',
  });

  const update = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const c = await api.createComplaint(form);
      push(`Complaint lodged: ${c.reference_no}`);
      nav(`/complaints/${c.id}`);
    } catch (err) {
      push(`Failed: ${err}`, 'error');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-eyebrow">Lodge a New Complaint</div>
      <h1 className="page-title">Complaint Intake</h1>
      <p className="page-subtitle">
        Record a customer grievance received by RBI through any channel. Once
        recorded, it can be forwarded to the relevant bank for resolution.
      </p>

      <form className="form" onSubmit={submit}>
        <h3 className="section">Customer Information</h3>
        <div className="form-row">
          <div className="field">
            <label>Customer Name</label>
            <input value={form.customer_name} required
                   onChange={e => update('customer_name', e.target.value)} />
          </div>
          <div className="field">
            <label>Customer Token (CBS ID)</label>
            <input value={form.customer_token_id} required
                   placeholder="CUST-9912034"
                   onChange={e => update('customer_token_id', e.target.value)} />
          </div>
        </div>
        <div className="form-row">
          <div className="field">
            <label>Email</label>
            <input type="email" value={form.customer_email}
                   onChange={e => update('customer_email', e.target.value)} />
          </div>
          <div className="field">
            <label>Mobile</label>
            <input value={form.customer_mobile}
                   placeholder="+91…"
                   onChange={e => update('customer_mobile', e.target.value)} />
          </div>
        </div>

        <h3 className="section" style={{ marginTop: 28 }}>Routing</h3>
        <div className="form-row">
          <div className="field">
            <label>Bank Code</label>
            <select value={form.bank_code} onChange={e => update('bank_code', e.target.value)}>
              <option value="HDFC">HDFC Bank</option>
              <option value="ICICI">ICICI Bank</option>
              <option value="SBI">State Bank of India</option>
              <option value="AXIS">Axis Bank</option>
              <option value="KOTAK">Kotak Mahindra</option>
            </select>
          </div>
          <div className="field">
            <label>Intent</label>
            <select value={form.intent_class}
                    onChange={e => update('intent_class', e.target.value)}>
              {INTENT_CLASSES.map(i => (
                <option key={i} value={i}>{i.replaceAll('_', ' ')}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Channel</label>
            <select value={form.channel}
                    onChange={e => update('channel', e.target.value)}>
              {CHANNELS.map(c => (
                <option key={c} value={c}>{c.replaceAll('_', ' ')}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Language</label>
            <select value={form.language}
                    onChange={e => update('language', e.target.value)}>
              {LANGUAGES.map(([k, name]) => (
                <option key={k} value={k}>{name}</option>
              ))}
            </select>
          </div>
        </div>

        <h3 className="section" style={{ marginTop: 28 }}>Complaint Text</h3>
        <div className="field">
          <textarea value={form.raw_text} required
                    placeholder="In the customer's own words, as received…"
                    onChange={e => update('raw_text', e.target.value)} />
        </div>

        <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
          <button type="submit" className="btn" disabled={busy}>
            {busy ? 'Recording…' : 'Lodge Complaint'}
          </button>
          <button type="button" className="btn ghost"
                  onClick={() => nav('/complaints')}>Cancel</button>
        </div>
      </form>
    </>
  );
}
