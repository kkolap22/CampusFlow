import { Component, useEffect, useState, useCallback } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import axios from "axios";
import {
  Award, Bell, CalendarDays, CheckCircle2, ChevronRight, ClipboardList,
  Download, Edit3, FileText, LayoutDashboard, LogOut, Menu, Plus, Search,
  Settings, Tags, Trash2, Users, XCircle,
} from "lucide-react";
import "@/App.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const api = axios.create({ baseURL: API, withCredentials: true });

let onUnauthorizedCallback = null;
const registerUnauthorizedHandler = (cb) => { onUnauthorizedCallback = cb; };

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401 && onUnauthorizedCallback) {
      onUnauthorizedCallback();
    }
    return Promise.reject(error);
  }
);

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>
          <h2 style={{ color: "#0f172a", marginBottom: "8px" }}>Something went wrong</h2>
          <p style={{ marginBottom: "16px" }}>An unexpected error occurred. Please refresh the page.</p>
          <button className="primary" onClick={() => window.location.reload()}>Refresh</button>
        </div>
      );
    }
    return this.props.children;
  }
}

const errorText = (e) => {
  const d = e?.response?.data?.detail;
  return Array.isArray(d) ? d.map((x) => x.msg).join(" ") : d || "Something went wrong.";
};
const fmtDate = (d) => (d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—");

/* ------------------------------- Auth ---------------------------------- */
function Auth({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ email: "", password: "", name: "", department: "BSc IT" });
  const [error, setError] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try { const r = await api.post(`/auth/${mode}`, form); onAuth(r.data); }
    catch (x) { setError(errorText(x)); }
  };
  return (
    <main className="auth-shell">
      <section className="auth-brand">
        <div className="brand-mark">CF</div>
        <p className="eyebrow">CAMPUSFLOW</p>
        <h1>Make every<br /><em>moment</em> count.</h1>
        <p>One calm workspace for the events that bring your college community together.</p>
        <div className="auth-stats">
          <span><strong>Campus</strong> Connected</span>
          <span><strong>Events</strong> Real-time</span>
        </div>
      </section>
      <section className="auth-panel">
        <div className="auth-box">
          <div className="mobile-mark brand-mark">CF</div>
          <p className="eyebrow">{mode === "login" ? "WELCOME BACK" : "JOIN THE CAMPUS"}</p>
          <h2>{mode === "login" ? "Sign in to your workspace" : "Create your account"}</h2>
          <p className="muted">{mode === "login" ? "Pick up where your campus story left off." : "Student accounts are ready in a few moments."}</p>
          <form onSubmit={submit}>
            {mode !== "login" && (
              <>
                <label>Full name<input data-testid="register-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
                <label>Department
                  <select data-testid="register-department-input" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} required>
                    <option value="BSc IT">BSc IT</option>
                    <option value="Computer Science">Computer Science</option>
                    <option value="Information Technology">Information Technology</option>
                    <option value="Engineering">Engineering</option>
                    <option value="Management">Management</option>
                    <option value="Commerce">Commerce</option>
                  </select>
                </label>
              </>
            )}
            <label>College email<input data-testid="auth-email-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></label>
            <label>Password<input data-testid="auth-password-input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required /></label>
            {error && <div data-testid="auth-error" className="error">{error}</div>}
            <button data-testid="auth-submit-button" className="primary full">
              {mode === "login" ? "Sign in" : "Create account"}<ChevronRight size={17} />
            </button>
          </form>
          <button data-testid="auth-mode-toggle" className="text-button" onClick={() => setMode(mode === "login" ? "register" : "login")}>
            {mode === "login" ? "New to CampusFlow? Create an account" : "Already have an account? Sign in"}
          </button>
        </div>
      </section>
    </main>
  );
}

/* ---------------------------- Layout / Nav ----------------------------- */
const commonNav = [
  { key: "overview", label: "Overview", icon: LayoutDashboard },
  { key: "events", label: "Events", icon: CalendarDays },
  { key: "registrations", label: "Registrations", icon: ClipboardList },
  { key: "certificates", label: "Certificates", icon: Award },
  { key: "announcements", label: "Announcements", icon: Bell },
];
const adminExtra = [
  { key: "reports", label: "Reports", icon: FileText },
  { key: "categories", label: "Categories", icon: Tags },
  { key: "users", label: "People", icon: Users },
];

function Layout({ user, onLogout, children, active, setActive }) {
  const [open, setOpen] = useState(false);
  const isAdmin = user.role === "admin";
  return (
    <div className="app-layout">
      <aside className={open ? "sidebar open" : "sidebar"}>
        <div className="side-brand">
          <span className="brand-mark small">CF</span>
          <span>Campus<span>Flow</span></span>
          <button data-testid="sidebar-close-button" className="icon-button mobile-only" onClick={() => setOpen(false)}><XCircle size={18} /></button>
        </div>
        <div className="workspace">
          <span className="avatar">{user.name?.slice(0, 2).toUpperCase()}</span>
          <div><b>{user.name}</b><small>{isAdmin ? "Event administrator" : user.department}</small></div>
        </div>
        <nav>
          {commonNav.map((n) => (
            <button key={n.key} data-testid={`nav-${n.key}-button`}
              className={active === n.key ? "nav-item active" : "nav-item"}
              onClick={() => { setActive(n.key); setOpen(false); }}>
              <n.icon size={18} />{n.label}
            </button>
          ))}
          {isAdmin && (
            <>
              <div className="nav-label">MANAGE</div>
              {adminExtra.map((n) => (
                <button key={n.key} data-testid={`nav-${n.key}-button`}
                  className={active === n.key ? "nav-item active" : "nav-item"}
                  onClick={() => { setActive(n.key); setOpen(false); }}>
                  <n.icon size={18} />{n.label}
                </button>
              ))}
            </>
          )}
        </nav>
        <div className="sidebar-bottom">
          <button data-testid="nav-profile-button" className={active === "profile" ? "nav-item active" : "nav-item"} onClick={() => setActive("profile")}>
            <Settings size={18} />My profile
          </button>
          <button data-testid="logout-button" className="nav-item logout" onClick={onLogout}><LogOut size={18} />Sign out</button>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <button data-testid="sidebar-menu-button" className="icon-button mobile-only" onClick={() => setOpen(true)}><Menu /></button>
          <div className="crumb"><span>Workspace</span><ChevronRight size={14} /><b>{[...commonNav, ...adminExtra].find((n) => n.key === active)?.label || active}</b></div>
          <div className="top-actions">
            <button data-testid="notifications-button" className="icon-button"><Bell size={19} /><i /></button>
            <div className="top-avatar">{user.name?.slice(0, 1)}</div>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

const Page = ({ title, subtitle, children, action }) => (
  <div className="page">
    <div className="page-heading">
      <div>
        <p className="eyebrow">{new Date().toLocaleDateString("en-IN", { weekday: "long", month: "long", day: "numeric" })}</p>
        <h1>{title}</h1>
        <p className="subtitle">{subtitle}</p>
      </div>
      {action}
    </div>
    {children}
  </div>
);
const SectionHeader = ({ title, action, onClick }) => (
  <div className="section-header">
    <h3>{title}</h3>
    {action && <button data-testid={`section-${title.toLowerCase().replaceAll(" ", "-")}-action`} className="link-button" onClick={onClick}>{action}<ChevronRight size={15} /></button>}
  </div>
);
const Empty = ({ text }) => <div data-testid="empty-state" className="empty"><FileText size={25} /><p>{text}</p></div>;
const Modal = ({ title, close, children }) => (
  <div className="modal-backdrop">
    <div className="modal">
      <div className="modal-heading"><h2>{title}</h2><button data-testid="modal-close-button" className="icon-button" onClick={close}><XCircle /></button></div>
      {children}
    </div>
  </div>
);

/* ------------------------------- Overview ------------------------------ */
function Overview({ user, go }) {
  const [stats, setStats] = useState(null);
  const [events, setEvents] = useState([]);
  const [ann, setAnn] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    Promise.all([api.get("/dashboard"), api.get("/events"), api.get("/announcements")])
      .then(([s, e, a]) => {
        if (mounted) {
          setStats(s.data);
          setEvents(e.data);
          setAnn(a.data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) setLoading(false);
      });
    return () => { mounted = false; };
  }, []);
  const cards = [
    ["Total events", stats?.total_events, "Across all categories", CalendarDays, "teal"],
    ["Participants", stats?.total_participants, "Registered students", Users, "orange"],
    ["Registrations", stats?.total_registrations, "All time", ClipboardList, "blue"],
    [user.role === "admin" ? "Upcoming events" : "Your registrations",
      user.role === "admin" ? stats?.upcoming_events : stats?.my_registrations,
      "Stay connected", CheckCircle2, "lime"],
  ];
  return (
    <Page title={user.role === "admin" ? "Good morning, administrator." : `Welcome back, ${user.name.split(" ")[0]}.`}
      subtitle="Here's what's happening across your campus today.">
      <div className="hero-strip">
        <div>
          <span className="eyebrow">{user.role === "admin" ? "CAMPUS PULSE" : "YOUR CAMPUS PULSE"}</span>
          <h2>Make room for what<br /><em>matters.</em></h2>
          <p>Keep every student in the loop, from first registration to final applause.</p>
        </div>
        <div className="hero-line"><span>THIS WEEK</span><strong>{stats?.upcoming_events || 0}</strong><small>upcoming events</small></div>
      </div>
      <div className="stats-grid">
        {cards.map(([l, v, s, I, c]) => (
          <div key={l} data-testid={`stat-${l.toLowerCase().replaceAll(" ", "-")}`} className="stat-card">
            <div className={`stat-icon ${c}`}><I size={19} /></div>
            <span>{l}</span><strong>{v ?? "—"}</strong><small>{s}</small>
          </div>
        ))}
      </div>
      <div className="content-grid">
        <section className="section-block">
          <SectionHeader title="Coming up" action="View all" onClick={() => go("events")} />
          <div className="mini-events">
            {events.slice(0, 3).map((e) => (
              <div key={e.id} data-testid={`upcoming-event-${e.id}`} className="mini-event">
                <img src={e.image} alt="" />
                <div><span>{e.category}</span><b>{e.title}</b><small>{fmtDate(e.date)} · {e.venue}</small></div>
                <ChevronRight size={17} />
              </div>
            ))}
            {!events.length && <Empty text="No events yet" />}
          </div>
        </section>
        <section className="section-block announcements">
          <SectionHeader title="Latest announcements" action="See all" onClick={() => go("announcements")} />
          {ann.slice(0, 3).map((a) => (
            <div key={a.id} data-testid={`announcement-${a.id}`} className="announcement">
              <div className="announcement-dot" />
              <div><b>{a.title}</b><p>{a.message}</p><small>{a.author} · {fmtDate(a.created_at)}</small></div>
            </div>
          ))}
          {!ann.length && <Empty text="No announcements yet" />}
        </section>
      </div>
    </Page>
  );
}

/* ------------------------------- Events -------------------------------- */
const emptyEvent = { title: "", description: "", category: "Technology", date: "", time: "10:00", venue: "", capacity: 50, status: "upcoming", image: "" };
function Events({ user }) {
  const [events, setEvents] = useState([]);
  const [cats, setCats] = useState([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [show, setShow] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyEvent);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    const qs = new URLSearchParams({ search, category, status }).toString();
    return Promise.all([api.get(`/events?${qs}`), api.get("/categories")])
      .then(([e, c]) => { setEvents(e.data); setCats(c.data); })
      .catch(() => setError("Events could not be loaded."))
      .finally(() => setLoading(false));
  }, [search, category, status]);
  useEffect(() => { load(); }, [load]);

  const openCreate = () => { setEditing(null); setForm({ ...emptyEvent, category: cats[0]?.name || "Technology" }); setShow(true); };
  const openEdit = (e) => { setEditing(e); setForm({ title: e.title, description: e.description, category: e.category, date: e.date, time: e.time, venue: e.venue, capacity: e.capacity, status: e.status, image: e.image || "" }); setShow(true); };

  const save = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const payload = { ...form, capacity: Number(form.capacity) };
      if (!payload.image) delete payload.image;
      if (editing) await api.put(`/events/${editing.id}`, payload);
      else await api.post("/events", payload);
      setShow(false);
      load();
    } catch (x) { setError(errorText(x)); }
  };

  const toggleReg = async (e) => {
    try {
      if (e.registered) await api.delete(`/events/${e.id}/register`);
      else await api.post(`/events/${e.id}/register`);
      load();
    } catch (x) { setError(errorText(x)); }
  };

  return (
    <Page title="Events" subtitle="Discover, shape, and celebrate the moments that define campus."
      action={user.role === "admin" && <button data-testid="create-event-button" className="primary" onClick={openCreate}><Plus size={17} /> New event</button>}>
      <div className="toolbar">
        <div className="search"><Search size={17} /><input data-testid="events-search-input" placeholder="Search events..." value={search} onChange={(e) => setSearch(e.target.value)} /></div>
        <select data-testid="events-category-filter" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {cats.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
        </select>
        <select data-testid="events-status-filter" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="upcoming">Upcoming</option>
          <option value="ongoing">Ongoing</option>
          <option value="completed">Completed</option>
        </select>
      </div>
      {loading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--muted)" }}>Loading events…</div>
      ) : (
        <div className="event-grid">
          {events.map((e) => (
            <article key={e.id} data-testid={`event-card-${e.id}`} className="event-card">
              <div className="event-image">
                <img src={e.image} alt="" /><span>{e.category}</span>
              </div>
              <div className="event-body">
                <div className="event-date">
                  <b>{new Date(e.date).toLocaleDateString("en-IN", { day: "2-digit" })}</b>
                  <small>{new Date(e.date).toLocaleDateString("en-IN", { month: "short" })}</small>
                </div>
                <div className="event-info">
                  <h3>{e.title}</h3>
                  <p>{e.description}</p>
                  <small>{e.time} · {e.venue}</small>
                </div>
              </div>
              <div className="event-footer">
                <span><Users size={14} /> {e.registration_count}/{e.capacity}</span>
                {user.role === "student" && (
                  <button data-testid={`event-register-${e.id}`} className={e.registered ? "outline success" : "primary small"} onClick={() => toggleReg(e)}>
                    {e.registered ? "Registered" : "Register"}
                  </button>
                )}
                {user.role === "admin" && (
                  <div style={{ display: "flex", gap: 6 }}>
                    <button data-testid={`event-edit-${e.id}`} className="icon-button" onClick={() => openEdit(e)}><Edit3 size={16} /></button>
                    <button data-testid={`event-delete-${e.id}`} className="icon-button danger" onClick={async () => { if (window.confirm("Delete this event?")) { await api.delete(`/events/${e.id}`); load(); } }}><Trash2 size={16} /></button>
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
      {!loading && !events.length && <Empty text="No events match your filters" />}
      {error && <div className="error toast-error">{error}</div>}
      {show && (
        <Modal title={editing ? "Edit event" : "Create a new event"} close={() => setShow(false)}>
          <form onSubmit={save} className="modal-form">
            <label>Event title<input data-testid="event-title-input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required /></label>
            <label>Description<textarea data-testid="event-description-input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required /></label>
            <label>Date<input data-testid="event-date-input" type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} required /></label>
            <label>Start time<input data-testid="event-time-input" type="time" value={form.time} onChange={(e) => setForm({ ...form, time: e.target.value })} required /></label>
            <label>Venue<input data-testid="event-venue-input" value={form.venue} onChange={(e) => setForm({ ...form, venue: e.target.value })} required /></label>
            <label>Capacity<input data-testid="event-capacity-input" type="number" min="1" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: e.target.value })} required /></label>
            <label>Category
              <select data-testid="event-category-input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                {cats.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
              </select>
            </label>
            <label>Status
              <select data-testid="event-status-input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                <option value="upcoming">Upcoming</option>
                <option value="ongoing">Ongoing</option>
                <option value="completed">Completed</option>
              </select>
            </label>
            <label>Image URL (optional)<input data-testid="event-image-input" value={form.image} onChange={(e) => setForm({ ...form, image: e.target.value })} placeholder="https://..." /></label>
            {error && <div className="error">{error}</div>}
            <button data-testid="event-save-button" className="primary full">{editing ? "Save changes" : "Create event"}</button>
          </form>
        </Modal>
      )}
    </Page>
  );
}

/* --------------------------- Registrations ----------------------------- */
function Registrations({ user }) {
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    return api.get("/registrations")
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);

  const update = async (id, status) => { setBusy(true); await api.patch(`/registrations/${id}?status=${status}`); await load(); setBusy(false); };
  const mark = async (id, present) => { setBusy(true); try { await api.post(`/registrations/${id}/attendance?present=${present}`); await load(); } catch (e) { alert(errorText(e)); } setBusy(false); };
  const unreg = async (event_id) => { if (window.confirm("Cancel this registration?")) { await api.delete(`/events/${event_id}/register`); load(); } };
  const isAdmin = user.role === "admin";

  return (
    <Page title="Registrations" subtitle={isAdmin ? "Approve participants and mark attendance." : "Track the events you've signed up for."}>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {isAdmin && <th>Participant</th>}
              <th>Event</th>
              <th>Applied</th>
              <th>Status</th>
              <th>Attendance</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} style={{ textAlign: "center", padding: 30, color: "var(--muted)" }}>Loading registrations…</td></tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id} data-testid={`registration-row-${r.id}`}>
                  {isAdmin && <td><b>{r.student_name}</b><small>{r.student_email}</small></td>}
                  <td><b>{r.event_title}</b><small>{fmtDate(r.event_date)}</small></td>
                  <td>{fmtDate(r.registered_at)}</td>
                  <td><span className={`status ${r.status}`}>{r.status}</span></td>
                  <td>
                    {r.attendance === true && <span className="status approved">Present</span>}
                    {r.attendance === false && <span className="status rejected">Absent</span>}
                    {r.attendance === null && <span className="status pending">Not marked</span>}
                  </td>
                  <td>
                    {isAdmin ? (
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        <button data-testid={`approve-registration-${r.id}`} className="icon-button success" title="Approve" disabled={busy} onClick={() => update(r.id, "approved")}><CheckCircle2 size={17} /></button>
                        <button data-testid={`reject-registration-${r.id}`} className="icon-button danger" title="Reject" disabled={busy} onClick={() => update(r.id, "rejected")}><XCircle size={17} /></button>
                        <button data-testid={`present-registration-${r.id}`} className="outline" title="Mark present" disabled={busy || r.status !== "approved"} onClick={() => mark(r.id, true)}>Present</button>
                        <button data-testid={`absent-registration-${r.id}`} className="outline" title="Mark absent" disabled={busy || r.status !== "approved"} onClick={() => mark(r.id, false)}>Absent</button>
                      </div>
                    ) : (
                      <button data-testid={`unregister-${r.id}`} className="outline" onClick={() => unreg(r.event_id)}>Unregister</button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        {!loading && !rows.length && <Empty text={isAdmin ? "No registrations to review" : "You haven't registered for any event yet"} />}
      </div>
    </Page>
  );
}

/* --------------------------- Certificates ------------------------------ */
function Certificates() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/certificates")
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  }, []);

  const download = (registration_id) => {
    window.open(`${API}/certificates/${registration_id}/download`, "_blank");
  };
  return (
    <Page title="Certificates" subtitle="A record of every event you completed. Download and share.">
      <div className="table-wrap">
        <table>
          <thead><tr><th>Event</th><th>Held on</th><th>Participant</th><th>Issued</th><th></th></tr></thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} style={{ textAlign: "center", padding: 30, color: "var(--muted)" }}>Loading certificates…</td></tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id} data-testid={`certificate-row-${r.registration_id}`}>
                  <td><b>{r.event_title}</b></td>
                  <td>{fmtDate(r.event_date)}</td>
                  <td>{r.student_name}</td>
                  <td>{fmtDate(r.issued_at)}</td>
                  <td><button data-testid={`certificate-download-${r.registration_id}`} className="primary small" onClick={() => download(r.registration_id)}><Download size={14} /> Download</button></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        {!loading && !rows.length && <Empty text="Certificates appear here after attendance is marked" />}
      </div>
    </Page>
  );
}

/* --------------------------- Announcements ----------------------------- */
function Announcements({ user }) {
  const [items, setItems] = useState([]);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({ title: "", message: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    return api.get("/announcements")
      .then((r) => setItems(r.data))
      .catch(() => setError("Announcements could not be loaded."))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);
  const save = async (e) => {
    e.preventDefault();
    try { await api.post("/announcements", form); setShow(false); setForm({ title: "", message: "" }); load(); }
    catch (x) { setError(errorText(x)); }
  };
  const del = async (id) => { if (window.confirm("Delete this announcement?")) { await api.delete(`/announcements/${id}`); load(); } };
  return (
    <Page title="Announcements" subtitle="A clear channel for the updates your community needs."
      action={user.role === "admin" && <button data-testid="create-announcement-button" className="primary" onClick={() => setShow(true)}><Plus size={17} /> New announcement</button>}>
      <div className="announcement-list">
        {error && <div data-testid="announcements-error" className="error">{error}</div>}
        {loading && <div style={{ padding: 30, textAlign: "center", color: "var(--muted)" }}>Loading announcements…</div>}
        {!loading && items.map((a) => (
          <div key={a.id} data-testid={`announcement-item-${a.id}`} className="announcement large">
            <div className="announcement-dot" />
            <div style={{ flex: 1 }}>
              <div className="announcement-top">
                <b>{a.title}</b>
                <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <small>{fmtDate(a.created_at)}</small>
                  {user.role === "admin" && <button data-testid={`announcement-delete-${a.id}`} className="icon-button danger" onClick={() => del(a.id)}><Trash2 size={15} /></button>}
                </div>
              </div>
              <p>{a.message}</p>
              <small>Posted by {a.author}</small>
            </div>
          </div>
        ))}
        {!loading && !items.length && !error && <Empty text="Announcements from your team will appear here" />}
      </div>
      {show && (
        <Modal title="Share an announcement" close={() => setShow(false)}>
          <form className="modal-form" onSubmit={save}>
            <label>Title<input data-testid="announcement-title-input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required /></label>
            <label>Message<textarea data-testid="announcement-message-input" value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} required /></label>
            <button data-testid="announcement-save-button" className="primary full">Publish announcement</button>
          </form>
        </Modal>
      )}
    </Page>
  );
}

/* ---------------------------- Categories ------------------------------- */
function Categories() {
  const [rows, setRows] = useState([]);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({ name: "", description: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    return api.get("/categories")
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);
  const save = async (e) => {
    e.preventDefault();
    setError("");
    try { await api.post("/categories", form); setShow(false); setForm({ name: "", description: "" }); load(); }
    catch (x) { setError(errorText(x)); }
  };
  const del = async (id) => { if (window.confirm("Delete category?")) { await api.delete(`/categories/${id}`); load(); } };
  return (
    <Page title="Categories" subtitle="Group every event under the right theme."
      action={<button data-testid="create-category-button" className="primary" onClick={() => setShow(true)}><Plus size={17} /> New category</button>}>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Name</th><th>Description</th><th></th></tr></thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={3} style={{ textAlign: "center", padding: 30, color: "var(--muted)" }}>Loading categories…</td></tr>
            ) : (
              rows.map((c) => (
                <tr key={c.id} data-testid={`category-row-${c.id}`}>
                  <td><b>{c.name}</b></td>
                  <td>{c.description || <span className="muted">—</span>}</td>
                  <td><button data-testid={`category-delete-${c.id}`} className="icon-button danger" onClick={() => del(c.id)}><Trash2 size={16} /></button></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        {!loading && !rows.length && <Empty text="No categories yet" />}
      </div>
      {show && (
        <Modal title="New category" close={() => setShow(false)}>
          <form className="modal-form" onSubmit={save}>
            <label>Name<input data-testid="category-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
            <label>Description<textarea data-testid="category-description-input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
            {error && <div className="error">{error}</div>}
            <button data-testid="category-save-button" className="primary full">Save category</button>
          </form>
        </Modal>
      )}
    </Page>
  );
}

/* ------------------------------ People --------------------------------- */
function People({ user }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    return api.get("/users")
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);
  const changeRole = async (id, role) => { await api.patch(`/users/${id}/role?role=${role}`); load(); };
  const del = async (id) => { if (window.confirm("Delete this user? All their registrations will be removed.")) { try { await api.delete(`/users/${id}`); load(); } catch (e) { alert(errorText(e)); } } };
  return (
    <Page title="People" subtitle="Manage administrators and student accounts.">
      <div className="table-wrap">
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Department</th><th>Role</th><th></th></tr></thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} style={{ textAlign: "center", padding: 30, color: "var(--muted)" }}>Loading users…</td></tr>
            ) : (
              rows.map((u) => (
                <tr key={u.id} data-testid={`user-row-${u.id}`}>
                  <td><b>{u.name}</b></td>
                  <td>{u.email}</td>
                  <td>{u.department}</td>
                  <td>
                    <select data-testid={`user-role-select-${u.id}`} value={u.role} disabled={u.id === user.id} onChange={(e) => changeRole(u.id, e.target.value)}>
                      <option value="admin">Admin</option>
                      <option value="student">Student</option>
                    </select>
                  </td>
                  <td>{u.id !== user.id && <button data-testid={`user-delete-${u.id}`} className="icon-button danger" onClick={() => del(u.id)}><Trash2 size={16} /></button>}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        {!loading && !rows.length && <Empty text="No users yet" />}
      </div>
    </Page>
  );
}

/* ------------------------------ Reports -------------------------------- */
function Reports() {
  const [rows, setRows] = useState([]);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/reports/events")
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  }, []);
  const filtered = rows.filter((r) => (!from || r.date >= from) && (!to || r.date <= to));
  const totals = filtered.reduce((a, r) => ({ registrations: a.registrations + r.registrations, attended: a.attended + r.attended, capacity: a.capacity + r.capacity }), { registrations: 0, attended: 0, capacity: 0 });
  return (
    <Page title="Reports" subtitle="Event-wise registrations, attendance and capacity utilisation.">
      <div className="toolbar">
        <label style={{ fontSize: 11, color: "#64748b" }}>From<input data-testid="report-from-input" type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
        <label style={{ fontSize: 11, color: "#64748b" }}>To<input data-testid="report-to-input" type="date" value={to} onChange={(e) => setTo(e.target.value)} /></label>
      </div>
      <div className="stats-grid" style={{ marginBottom: 25 }}>
        <div className="stat-card"><div className="stat-icon teal"><CalendarDays size={19} /></div><span>Events in range</span><strong>{filtered.length}</strong><small>Applied filters</small></div>
        <div className="stat-card"><div className="stat-icon blue"><ClipboardList size={19} /></div><span>Registrations</span><strong>{totals.registrations}</strong><small>All statuses</small></div>
        <div className="stat-card"><div className="stat-icon lime"><CheckCircle2 size={19} /></div><span>Attended</span><strong>{totals.attended}</strong><small>Marked present</small></div>
        <div className="stat-card"><div className="stat-icon orange"><Users size={19} /></div><span>Capacity</span><strong>{totals.capacity}</strong><small>Combined seats</small></div>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Event</th><th>Category</th><th>Date</th><th>Registrations</th><th>Approved</th><th>Pending</th><th>Attended</th><th>Fill %</th></tr></thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} style={{ textAlign: "center", padding: 30, color: "var(--muted)" }}>Loading report…</td></tr>
            ) : (
              filtered.map((r) => (
                <tr key={r.id} data-testid={`report-row-${r.id}`}>
                  <td><b>{r.title}</b></td>
                  <td>{r.category}</td>
                  <td>{fmtDate(r.date)}</td>
                  <td>{r.registrations}</td>
                  <td>{r.approved}</td>
                  <td>{r.pending}</td>
                  <td>{r.attended}</td>
                  <td>{r.capacity ? Math.round((r.registrations / r.capacity) * 100) : 0}%</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        {!loading && !filtered.length && <Empty text="No events match the selected range" />}
      </div>
    </Page>
  );
}

/* ------------------------------ Profile -------------------------------- */
function Profile({ user, refresh }) {
  const [form, setForm] = useState({ name: user.name, department: user.department || "", phone: user.phone || "" });
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const save = async (e) => {
    e.preventDefault();
    setMsg(""); setError("");
    try { await api.put("/profile", form); setMsg("Profile updated successfully."); refresh(); }
    catch (x) { setError(errorText(x)); }
  };
  return (
    <Page title="My profile" subtitle="Keep your account details up to date.">
      <div style={{ maxWidth: 520, background: "#fff", border: "1px solid var(--line)", borderRadius: 10, padding: 30 }}>
        <form onSubmit={save}>
          <label>Full name<input data-testid="profile-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
          <label>Email<input value={user.email} disabled /></label>
          <label>Department<input data-testid="profile-department-input" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} required /></label>
          <label>Phone<input data-testid="profile-phone-input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
          <label>Role<input value={user.role} disabled /></label>
          {msg && <div data-testid="profile-success" style={{ background: "#dcfce7", color: "#166534", padding: 10, borderRadius: 6, fontSize: 12, marginBottom: 10 }}>{msg}</div>}
          {error && <div className="error">{error}</div>}
          <button data-testid="profile-save-button" className="primary full">Save changes</button>
        </form>
      </div>
    </Page>
  );
}

/* ------------------------------- Shell --------------------------------- */
function AppShell({ user, onLogout, refresh }) {
  const [active, setActive] = useState("overview");
  const isAdmin = user.role === "admin";
  const screens = {
    overview: <Overview user={user} go={setActive} />,
    events: <Events user={user} />,
    registrations: <Registrations user={user} />,
    certificates: <Certificates />,
    announcements: <Announcements user={user} />,
    profile: <Profile user={user} refresh={refresh} />,
    reports: isAdmin ? <Reports /> : <Overview user={user} go={setActive} />,
    categories: isAdmin ? <Categories /> : <Overview user={user} go={setActive} />,
    users: isAdmin ? <People user={user} /> : <Overview user={user} go={setActive} />,
  };
  return (
    <Layout user={user} onLogout={onLogout} active={active} setActive={setActive}>
      {screens[active] || screens.overview}
    </Layout>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const refresh = useCallback(() => api.get("/auth/me").then((r) => setUser(r.data)).catch(() => {}), []);

  useEffect(() => {
    registerUnauthorizedHandler(() => setUser(null));
  }, []);

  useEffect(() => { refresh().finally(() => setChecking(false)); }, [refresh]);
  if (checking) return <div className="loading-screen">Loading your workspace…</div>;
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={
            user ? <AppShell user={user} refresh={refresh} onLogout={async () => { await api.post("/auth/logout"); setUser(null); }} /> : <Auth onAuth={setUser} />
          } />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
export default App;
