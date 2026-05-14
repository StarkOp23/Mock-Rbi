/**
 * Typed API client.
 * VITE_API_BASE_URL and VITE_API_TOKEN are set on Render at build time.
 */

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api/v1';
const TOKEN = import.meta.env.VITE_API_TOKEN as string | undefined;

export interface ComplaintListItem {
  id: string;
  reference_no: string;
  customer_name: string;
  bank_code: string;
  intent_class: string;
  status: string;
  received_at: string;
  language: string;
}

export interface Complaint extends ComplaintListItem {
  customer_email: string | null;
  customer_mobile: string | null;
  customer_token_id: string;
  channel: string;
  raw_text: string;
  closed_at: string | null;
}

export interface Forwarding {
  id: string;
  bank_code: string;
  forwarded_at: string;
  http_status: number | null;
  bank_run_id: string | null;
  error_message: string | null;
}

export interface BankResponse {
  id: string;
  bank_code: string;
  received_at: string;
  outcome: string;
  compensation_inr: number;
  tat_days: number;
  breached_30_day: boolean;
  customer_letter: string | null;
  bank_run_id: string | null;
}

export interface ComplaintDetail {
  complaint: Complaint;
  forwardings: Forwarding[];
  responses: BankResponse[];
}

export interface DashboardStats {
  total_complaints: number;
  by_status: Record<string, number>;
  by_bank: Record<string, number>;
  by_intent: Record<string, number>;
  open_count: number;
  avg_tat_days: number | null;
  breach_count: number;
}

export interface AuditEvent {
  id: number;
  occurred_at: string;
  actor: string;
  event_type: string;
  resource_type: string | null;
  resource_id: string | null;
  outcome: string;
  detail: Record<string, unknown>;
}

export interface ForwardResult {
  forwarding_id: string;
  bank_code: string;
  bank_run_id: string | null;
  http_status: number | null;
  success: boolean;
  detail: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (TOKEN) headers['Authorization'] = `Bearer ${TOKEN}`;

  const resp = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${body}`);
  }
  if (resp.status === 204) return undefined as unknown as T;
  return resp.json();
}

export const api = {
  // dashboard
  dashboardStats: () => request<DashboardStats>('/dashboard/stats'),

  // complaints
  listComplaints: (params: Partial<{ bank_code: string; status: string; intent: string; limit: number }> = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== '' && q.set(k, String(v)));
    const qs = q.toString();
    return request<ComplaintListItem[]>(`/complaints${qs ? '?' + qs : ''}`);
  },
  getComplaint: (id: string) => request<ComplaintDetail>(`/complaints/${id}`),
  createComplaint: (payload: Record<string, unknown>) =>
    request<Complaint>('/complaints', { method: 'POST', body: JSON.stringify(payload) }),

  // forwarding
  forwardToBank: (complaintId: string) =>
    request<ForwardResult>(`/forwarding/${complaintId}/forward`, { method: 'POST' }),

  // audit
  audit: (params: Partial<{ event_type: string; resource_id: string; limit: number }> = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== '' && q.set(k, String(v)));
    const qs = q.toString();
    return request<AuditEvent[]>(`/audit${qs ? '?' + qs : ''}`);
  },
};
