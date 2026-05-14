import { useEffect, useState, createContext, useContext, useCallback } from 'react';
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import Dashboard       from './pages/Dashboard';
import ComplaintIntake from './pages/ComplaintIntake';
import ComplaintList   from './pages/ComplaintList';
import ComplaintDetail from './pages/ComplaintDetail';
import AuditLog        from './pages/AuditLog';
import BankInbox       from './pages/BankInbox';

// --- Toast context ---
interface Toast { msg: string; kind: 'info' | 'error'; id: number }
interface ToastCtx { push: (msg: string, kind?: 'info' | 'error') => void }

const ToastContext = createContext<ToastCtx>({ push: () => {} });
export const useToast = () => useContext(ToastContext);

export default function App() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((msg: string, kind: 'info' | 'error' = 'info') => {
    const id = Date.now() + Math.random();
    setToasts(t => [...t, { msg, kind, id }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4500);
  }, []);

  // Date string for the topbar — refreshed each minute
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(t);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      <div className="app">
        <aside className="sidebar">
          <div className="sidebar-brand">RBI&nbsp;CMS</div>
          <div className="sidebar-sub">Reserve Bank of India · Demo</div>
          <nav className="sidebar-nav">
            <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'active' : ''}>Dashboard</NavLink>
            <NavLink to="/intake"    className={({ isActive }) => isActive ? 'active' : ''}>New Complaint</NavLink>
            <NavLink to="/complaints" className={({ isActive }) => isActive ? 'active' : ''}>Complaints</NavLink>
            <NavLink to="/inbox"     className={({ isActive }) => isActive ? 'active' : ''}>Bank Responses</NavLink>
            <NavLink to="/audit"     className={({ isActive }) => isActive ? 'active' : ''}>Audit Log</NavLink>
          </nav>
          <div className="sidebar-footer">
            For Demonstration<br/>Purposes Only
          </div>
        </aside>

        <main className="main">
          <div className="topbar">
            <div>
              <div className="page-eyebrow">Complaints Management System</div>
              <div className="page-title" style={{ fontSize: 22, marginBottom: 0 }}>
                Customer Grievance Intake & Routing
              </div>
            </div>
            <div className="topbar-meta">
              {now.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
            </div>
          </div>

          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard"          element={<Dashboard />} />
            <Route path="/intake"             element={<ComplaintIntake />} />
            <Route path="/complaints"         element={<ComplaintList />} />
            <Route path="/complaints/:id"     element={<ComplaintDetail />} />
            <Route path="/inbox"              element={<BankInbox />} />
            <Route path="/audit"              element={<AuditLog />} />
          </Routes>
        </main>

        {toasts.map(t => (
          <div key={t.id} className={`toast ${t.kind === 'error' ? 'error' : ''}`}>{t.msg}</div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
