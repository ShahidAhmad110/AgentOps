"use client";

import {
  Activity,
  ArrowDown,
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Clock3,
  Eye,
  FileText,
  Filter,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  MessageSquareText,
  MoreHorizontal,
  Paperclip,
  Plus,
  Search,
  Send,
  Settings2,
  Shield,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  UserCheck,
  UserRound,
  UserX,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import {
  AgentResult,
  AgentRunRecord,
  ApiError,
  Conversation,
  DocumentRecord,
  Message,
  SearchResult,
  Task,
  TaskDetail,
  TokenResponse,
  User,
  UserStats,
  apiRequest,
  jsonBody,
} from "@/lib/api";

type View = "overview" | "chat" | "documents" | "tasks" | "runs" | "users";
type Notice = { kind: "error" | "success"; text: string };
type MessageEvidence = Pick<AgentResult, "retrieved_sources" | "tool_calls">;

const statusLabels: Record<string, string> = {
  TODO: "To do",
  IN_PROGRESS: "In progress",
  BLOCKED: "Blocked",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
};

function humanError(error: unknown) {
  if (error instanceof ApiError && error.status === 401) return "Your session has expired. Sign in again.";
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

function dateLabel(value?: string | null) {
  if (!value) return "No due date";
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(new Date(value));
}

function initials(name: string) {
  return name.slice(0, 2).toUpperCase();
}

export default function AgentOpsWorkspace() {
  const [token, setToken] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [view, setView] = useState<View>("overview");
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loading, setLoading] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [runs, setRuns] = useState<AgentRunRecord[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [activeConversation, setActiveConversation] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [messageEvidence, setMessageEvidence] = useState<Record<string, MessageEvidence>>({});
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [taskDetail, setTaskDetail] = useState<TaskDetail | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const tokenRef = useRef("");
  const clearSessionRef = useRef<() => void>(() => undefined);
  tokenRef.current = token;
  clearSessionRef.current = () => {
    window.sessionStorage.removeItem("agentops.token");
    setToken("");
    setUser(null);
    setConversations([]);
    setDocuments([]);
    setTasks([]);
    setRuns([]);
    setUsers([]);
    setMessages([]);
    setMessageEvidence({});
    setLoading(false);
    setActiveConversation(null);
    setSearchResult(null);
    setTaskDetail(null);
    setNotice(null);
    setView("overview");
    setSidebarOpen(false);
  };

  useEffect(() => {
    const handleUnauthorized = (event: Event) => {
      const failedToken = (event as CustomEvent<{ token: string }>).detail?.token;
      if (failedToken && failedToken === tokenRef.current) clearSessionRef.current();
    };
    window.addEventListener("agentops:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("agentops:unauthorized", handleUnauthorized);
  }, []);

  useEffect(() => {
    const savedToken = window.sessionStorage.getItem("agentops.token");
    if (!savedToken) {
      setAuthReady(true);
      return;
    }
    setToken(savedToken);
    apiRequest<User>("/auth/me", savedToken)
      .then((currentUser) => setUser(currentUser))
      .catch(() => clearSessionRef.current())
      .finally(() => setAuthReady(true));
  }, []);

  useEffect(() => {
    if (!user || !token) return;
    void refreshWorkspace();
  }, [user, token]);

  async function refreshWorkspace() {
    const requestToken = token;
    setLoading(true);
    const promises: Promise<unknown>[] = [
      apiRequest<Conversation[]>("/conversations?limit=50&offset=0", token),
      apiRequest<DocumentRecord[]>("/documents?limit=50&offset=0", token),
      apiRequest<Task[]>("/tasks?limit=50&offset=0", token),
      apiRequest<AgentRunRecord[]>("/agent-runs?limit=50&offset=0", token),
    ];
    if (user?.role === "admin" || user?.role === "supervisor") {
      promises.push(apiRequest<User[]>("/users?limit=100&offset=0", token));
    }
    const results = await Promise.allSettled(promises);
    if (tokenRef.current !== requestToken) return;
    if (results[0].status === "fulfilled") setConversations(results[0].value as Conversation[]);
    if (results[1].status === "fulfilled") setDocuments(results[1].value as DocumentRecord[]);
    if (results[2].status === "fulfilled") setTasks(results[2].value as Task[]);
    if (results[3].status === "fulfilled") setRuns(results[3].value as AgentRunRecord[]);
    if (results[4] && results[4].status === "fulfilled") setUsers(results[4].value as User[]);
    const rejected = results.find((item) => item.status === "rejected");
    if (rejected && rejected.status === "rejected") setNotice({ kind: "error", text: humanError(rejected.reason) });
    setLoading(false);
  }

  async function selectConversation(conversationId: string) {
    const requestToken = token;
    setActiveConversation(conversationId);
    setView("chat");
    setNotice(null);
    try {
      const conversation = await apiRequest<Conversation & { messages: Message[] }>(
        `/conversations/${conversationId}`,
        token,
      );
      if (tokenRef.current !== requestToken) return;
      setMessages(conversation.messages);
      const evidence: Record<string, MessageEvidence> = {};
      const conversationRuns = runs.filter((run) => run.conversation_id === conversationId);
      for (const [index, message] of conversation.messages.entries()) {
        if (message.role !== "assistant") continue;
        const precedingUserMessage = [...conversation.messages.slice(0, index)].reverse()
          .find((item) => item.role === "user");
        const matchingRun = conversationRuns.find((run) => run.request === precedingUserMessage?.content);
        if (matchingRun) {
          evidence[message.id] = {
            retrieved_sources: matchingRun.retrieved_sources,
            tool_calls: matchingRun.tool_calls,
          };
        }
      }
      setMessageEvidence(evidence);
    } catch (error) {
      if (tokenRef.current === requestToken) setNotice({ kind: "error", text: humanError(error) });
    }
  }

  async function createConversation() {
    const requestToken = token;
    setLoading(true);
    setNotice(null);
    try {
      const conversation = await apiRequest<Conversation>("/conversations", token, {
        method: "POST",
        body: jsonBody({ title: "New conversation" }),
      });
      if (tokenRef.current !== requestToken) return;
      setConversations((current) => [conversation, ...current]);
      setActiveConversation(conversation.id);
      setMessages([]);
      setMessageEvidence({});
      setView("chat");
    } catch (error) {
      if (tokenRef.current === requestToken) setNotice({ kind: "error", text: humanError(error) });
    } finally {
      setLoading(false);
    }
  }

  function signOut() {
    clearSessionRef.current();
  }

  if (!authReady) return <div className="boot-screen"><LoaderCircle className="spin" /> Loading your workspace</div>;
  if (!user || !token) {
    return (
      <AuthScreen
        onAuthenticated={(response) => {
          clearSessionRef.current();
          window.sessionStorage.setItem("agentops.token", response.access_token);
          setToken(response.access_token);
          setUser(response.user);
          setNotice(null);
        }}
      />
    );
  }

  const viewTitle: Record<View, string> = {
    overview: "Overview",
    chat: "AI workspace",
    documents: "Knowledge library",
    tasks: "Task board",
    runs: "Agent runs",
    users: "User management",
  };

  return (
    <div className="app-frame">
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <a className="brand" href="#overview" onClick={(event) => { event.preventDefault(); setView("overview"); }}>
          <span className="brand-mark"><span /></span>
          <span>agent<span className="brand-light">ops</span><small>OPERATIONS CONSOLE</small></span>
        </a>
        <div className="workspace-chip"><span className="workspace-dot" /> Workspace <ChevronDown size={14} /></div>
        <nav className="primary-nav" aria-label="Primary navigation">
          <p className="nav-label">Workspace</p>
          <NavButton active={view === "overview"} icon={<LayoutDashboard size={17} />} label="Overview" onClick={() => { setView("overview"); setSidebarOpen(false); }} />
          <NavButton active={view === "chat"} icon={<MessageSquareText size={17} />} label="AI workspace" onClick={() => { setView("chat"); setSidebarOpen(false); }} />
          <NavButton active={view === "documents"} icon={<FileText size={17} />} label="Knowledge" count={documents.length} onClick={() => { setView("documents"); setSidebarOpen(false); }} />
          <NavButton active={view === "tasks"} icon={<CheckCircle2 size={17} />} label="Tasks" count={tasks.filter((task) => task.status !== "COMPLETED" && task.status !== "CANCELLED").length} onClick={() => { setView("tasks"); setSidebarOpen(false); }} />
          <NavButton active={view === "runs"} icon={<Activity size={17} />} label="Agent runs" count={runs.length} onClick={() => { setView("runs"); setSidebarOpen(false); }} />
          {(user.role === "admin" || user.role === "supervisor") && (
            <NavButton active={view === "users"} icon={<UserRound size={17} />} label="Users" count={users.length} onClick={() => { setView("users"); setSidebarOpen(false); }} />
          )}
        </nav>
        <div className="sidebar-section-title"><span className="nav-label">Recent conversations</span><button className="icon-button mini" onClick={() => void createConversation()} aria-label="New conversation" title="New conversation"><Plus size={15} /></button></div>
        <div className="conversation-list">
          {conversations.slice(0, 7).map((conversation) => (
            <button key={conversation.id} className={`conversation-link ${activeConversation === conversation.id ? "selected" : ""}`} onClick={() => void selectConversation(conversation.id)}>
              <span className="conversation-indicator" />
              <span>{conversation.title || "Untitled conversation"}</span>
            </button>
          ))}
          {!conversations.length && <p className="sidebar-empty">Your conversations will appear here.</p>}
        </div>
        <div className="sidebar-bottom">
          <div className="user-mini"><span className="avatar">{initials(user.username)}</span><span className="user-meta"><strong>{user.username}</strong><small>{user.role} · {user.email}</small></span><button className="icon-button mini" onClick={signOut} title="Sign out" aria-label="Sign out"><LogOut size={15} /></button></div>
        </div>
      </aside>

      {sidebarOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}

      <main className="main-area">
        <header className="topbar">
          <button className="menu-toggle icon-button" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Settings2 size={18} /></button>
          <div className="breadcrumb"><span>Workspace</span><ArrowRight size={13} /><strong>{viewTitle[view]}</strong></div>
          <div className="topbar-actions">
            <span className="connection-indicator"><span /> API connected</span>
            <button className="icon-button" title="Refresh workspace" aria-label="Refresh workspace" onClick={() => void refreshWorkspace()}><ArrowDown size={16} className={loading ? "spin" : ""} /></button>
            <span className="avatar avatar-small">{initials(user.username)}</span>
          </div>
        </header>
        {notice && <NoticeBanner notice={notice} onDismiss={() => setNotice(null)} />}
        <section className="content-area">
          {view === "overview" && <Overview user={user} conversations={conversations} documents={documents} tasks={tasks} runs={runs} users={users} loading={loading} onNavigate={setView} onNewConversation={() => void createConversation()} />}
          {view === "chat" && <ChatView token={token} conversations={conversations} activeConversation={activeConversation} messages={messages} messageEvidence={messageEvidence} loading={loading} onCreateConversation={() => void createConversation()} onSelectConversation={(id) => void selectConversation(id)} onMessages={(items) => { if (tokenRef.current === token) setMessages(items); }} onMessageEvidence={(id, evidence) => { if (tokenRef.current === token) setMessageEvidence((current) => ({ ...current, [id]: evidence })); }} onRun={() => { if (tokenRef.current === token) void refreshWorkspace(); }} onNotice={(message) => { if (tokenRef.current === token) setNotice(message); }} />}
          {view === "documents" && <DocumentsView token={token} documents={documents} searchResult={searchResult} onSearchResult={setSearchResult} onDocuments={(items) => { if (tokenRef.current === token) setDocuments(items); }} onNotice={(message) => { if (tokenRef.current === token) setNotice(message); }} />}
          {view === "tasks" && <TasksView token={token} user={user} tasks={tasks} onTasks={(items) => { if (tokenRef.current === token) setTasks(items); }} detail={taskDetail} onDetail={(item) => { if (tokenRef.current === token) setTaskDetail(item); }} onNotice={setNotice} />}
          {view === "runs" && <RunsView runs={runs} />}
          {view === "users" && <UsersView token={token} currentUser={user} users={users} onUsers={(items) => { if (tokenRef.current === token) setUsers(items); }} onNotice={(message) => { if (tokenRef.current === token) setNotice(message); }} />}
        </section>
        <footer className="footer-line"><span>AgentOps</span><span>Organization-scoped workspace</span><span><Shield size={12} /> Protected session</span></footer>
      </main>
    </div>
  );
}

function NavButton({ active, icon, label, count, onClick }: { active: boolean; icon: React.ReactNode; label: string; count?: number; onClick: () => void }) {
  return <button className={`nav-button ${active ? "active" : ""}`} onClick={onClick}>{icon}<span>{label}</span>{count !== undefined && <small>{count}</small>}</button>;
}

function NoticeBanner({ notice, onDismiss }: { notice: Notice; onDismiss: () => void }) {
  return <div className={`notice notice-${notice.kind}`} role="status"><CircleAlert size={16} /><span>{notice.text}</span><button className="icon-button mini" onClick={onDismiss} aria-label="Dismiss message"><X size={14} /></button></div>;
}

function AuthScreen({ onAuthenticated }: { onAuthenticated: (response: TokenResponse) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const username = String(data.get("username") ?? "").trim();
    const password = String(data.get("password") ?? "");
    const orgSlug = String(data.get("organization_slug") ?? "")
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9-]/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");
    const payload = mode === "login"
      ? { username_or_email: username, password }
      : {
          username,
          email: String(data.get("email") ?? "").trim().toLowerCase(),
          password,
          organization_name: String(data.get("organization_name") ?? "").trim(),
          organization_slug: orgSlug || "default-org",
        };
    try {
      const response = await apiRequest<TokenResponse>(`/auth/${mode}`, undefined, { method: "POST", body: jsonBody(payload) });
      onAuthenticated(response);
    } catch (requestError) {
      setError(humanError(requestError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-brand-panel">
        <div className="auth-brand-lockup"><span className="brand-mark"><span /></span><span>agent<span className="brand-light">ops</span></span></div>
        <div className="auth-editorial"><p className="eyebrow">OPERATIONS INTELLIGENCE</p><h1>Clarity for the work that matters.</h1><p>Bring organizational knowledge, conversations, and operational tasks into one focused workspace.</p></div>
        <div className="auth-panel-foot"><span>01 / KNOWLEDGE</span><span>02 / EXECUTION</span><span>03 / TRACEABILITY</span></div>
      </section>
      <section className="auth-form-panel">
        <div className="auth-form-wrap">
          <p className="eyebrow">AGENTOPS CONSOLE</p>
          <h2>{mode === "login" ? "Welcome back" : "Create your workspace"}</h2>
          <p className="auth-subtitle">{mode === "login" ? "Sign in with your AgentOps account." : "Set up your account and organization."}</p>
          <div className="auth-tabs" role="tablist"><button className={mode === "login" ? "selected" : ""} onClick={() => { setMode("login"); setError(""); }}>Sign in</button><button className={mode === "register" ? "selected" : ""} onClick={() => { setMode("register"); setError(""); }}>Register</button></div>
          {error && <div className="form-error"><CircleAlert size={15} />{error}</div>}
          <form className="auth-form" onSubmit={submit}>
            {mode === "register" && <>
              <label>Username<input name="username" minLength={3} required autoComplete="username" placeholder="e.g. jordan.lee" /></label>
              <label>Email<input name="email" type="email" required autoComplete="email" placeholder="name@company.com" /></label>
              <label>Password<input name="password" type="password" minLength={8} required autoComplete="new-password" placeholder="At least 8 characters" /></label>
              <div className="form-two"><label>Organization<input name="organization_name" required maxLength={255} placeholder="Northstar Operations" /></label><label>URL slug<input name="organization_slug" required minLength={1} maxLength={100} placeholder="northstar-ops" /></label></div>
            </>}
            {mode === "login" && <>
              <label>Username or email<input name="username" required autoComplete="username" placeholder="you@company.com" /></label>
              <label>Password<input name="password" type="password" required autoComplete="current-password" placeholder="Your password" /></label>
            </>}
            <button className="button button-primary button-wide" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <ArrowRight size={17} />}{mode === "login" ? "Sign in to workspace" : "Create account"}</button>
          </form>
          <p className="auth-legal"><Shield size={13} /> Access is scoped to your authenticated organization.</p>
        </div>
        <span className="auth-copyright">AGENTOPS · OPERATIONS CONSOLE</span>
      </section>
    </main>
  );
}

function Overview({ user, conversations, documents, tasks, runs, users = [], loading, onNavigate, onNewConversation }: {
  user: User; conversations: Conversation[]; documents: DocumentRecord[]; tasks: Task[]; runs: AgentRunRecord[]; users?: User[]; loading: boolean;
  onNavigate: (view: View) => void; onNewConversation: () => void;
}) {
  const activeTasks = tasks.filter((task) => !["COMPLETED", "CANCELLED"].includes(task.status));
  const completedTasks = tasks.filter((task) => task.status === "COMPLETED");
  return <div className="page-stack">
    <div className="page-heading heading-with-action"><div><p className="eyebrow">MONDAY, OPERATIONS OVERVIEW</p><h1>Good to see you, {user.username}.</h1><p className="muted">Your organization’s knowledge and work, at a glance.</p></div><button className="button button-primary" onClick={onNewConversation}><Plus size={16} /> New conversation</button></div>
    <div className="metric-grid">
      <Metric label="Open tasks" value={activeTasks.length} detail={`${completedTasks.length} completed`} icon={<CheckCircle2 size={17} />} accent="mint" onClick={() => onNavigate("tasks")} />
      <Metric label="Knowledge files" value={documents.length} detail={`${documents.filter((document) => document.status === "READY").length} ready to search`} icon={<FileText size={17} />} accent="amber" onClick={() => onNavigate("documents")} />
      <Metric label="Conversations" value={conversations.length} detail="Your recent activity" icon={<MessageSquareText size={17} />} accent="coral" onClick={() => onNavigate("chat")} />
      <Metric label="Agent runs" value={runs.length} detail="Persisted history" icon={<Activity size={17} />} accent="blue" onClick={() => onNavigate("runs")} />
    </div>
    <div className="overview-grid">
      <section className="surface task-overview"><div className="section-heading"><div><p className="eyebrow">PRIORITIES</p><h2>Tasks in motion</h2></div><button className="text-button" onClick={() => onNavigate("tasks")}>All tasks <ArrowRight size={14} /></button></div>
        {loading ? <LoadingRows /> : activeTasks.slice(0, 5).map((task) => <TaskRow key={task.id} task={task} onClick={() => onNavigate("tasks")} />)}
        {!loading && !activeTasks.length && <EmptyState title="No open tasks" copy="You’re clear for now. Create a task when work needs tracking." action="View task board" onClick={() => onNavigate("tasks")} />}
      </section>
      <section className="surface recent-conversations"><div className="section-heading"><div><p className="eyebrow">KNOWLEDGE WORK</p><h2>Recent conversations</h2></div><button className="text-button" onClick={() => onNavigate("chat")}>Open workspace <ArrowRight size={14} /></button></div>
        {loading ? <LoadingRows /> : conversations.slice(0, 4).map((conversation) => <button className="recent-conversation" key={conversation.id} onClick={() => onNavigate("chat")}><span className="conversation-icon"><MessageSquareText size={15} /></span><span><strong>{conversation.title || "Untitled conversation"}</strong><small>Updated {dateLabel(conversation.updated_at)}</small></span><ArrowRight size={14} /></button>)}
        {!loading && !conversations.length && <EmptyState title="Start a conversation" copy="Ask a question or work through an operational task." action="Open AI workspace" onClick={() => onNavigate("chat")} />}
      </section>
    </div>
    <div className="overview-bottom">
      <section className="surface documents-overview"><div className="section-heading"><div><p className="eyebrow">ORGANIZATIONAL KNOWLEDGE</p><h2>Recently added</h2></div><button className="text-button" onClick={() => onNavigate("documents")}>Library <ArrowRight size={14} /></button></div>
        {documents.slice(0, 3).map((document) => <div className="document-row" key={document.id}><span className="file-type">{document.file_extension.replace(".", "").slice(0, 4).toUpperCase()}</span><span className="document-title"><strong>{document.filename}</strong><small>{formatBytes(document.size_bytes)}</small></span><StatusPill status={document.status} /></div>)}
        {!documents.length && <p className="muted empty-inline">No documents uploaded yet.</p>}
      </section>
      <section className="surface system-overview"><div className="section-heading"><div><p className="eyebrow">ACTIVITY</p><h2>Workspace status</h2></div><span className="live-tag"><span /> LIVE</span></div>
        <div className="system-line"><span className="system-check"><Check size={13} /></span><span><strong>API connection</strong><small>Authenticated requests available</small></span><span className="system-state">Ready</span></div>
        <div className="system-line"><span className="system-check"><Check size={13} /></span><span><strong>Knowledge retrieval</strong><small>{documents.filter((item) => item.status === "READY").length} indexed documents</small></span><span className="system-state">Ready</span></div>
        <div className="system-line"><span className="system-check"><Check size={13} /></span><span><strong>Session</strong><small>{user.role} access · organization scoped</small></span><span className="system-state">Secure</span></div>
      </section>
    </div>
    <section className="surface dashboard-runs"><div className="section-heading"><div><p className="eyebrow">TRACEABILITY</p><h2>Recent agent runs</h2></div><button className="text-button" onClick={() => onNavigate("runs")}>Run history <ArrowRight size={14} /></button></div>
      {loading ? <LoadingRows /> : runs.slice(0, 4).map((run) => <button className="dashboard-run-row" key={run.run_id} onClick={() => onNavigate("runs")}><span className={`run-icon ${run.status.toLowerCase() === "completed" ? "run-good" : "run-bad"}`}>{run.status.toLowerCase() === "completed" ? <CheckCircle2 size={14} /> : <Activity size={14} />}</span><span className="dashboard-run-description"><strong>{run.request}</strong><small>{new Date(run.started_at).toLocaleString()} · {run.duration_ms === null ? "In progress" : formatDuration(run.duration_ms)}</small></span><StatusPill status={run.status.toUpperCase()} /><ArrowRight size={14} /></button>)}
      {!loading && runs.length === 0 && <p className="muted empty-inline">No persisted agent activity yet.</p>}
    </section>
  </div>;
}

function Metric({ label, value, detail, icon, accent, onClick }: { label: string; value: number; detail: string; icon: React.ReactNode; accent: string; onClick: () => void }) {
  return <button className={`metric-card metric-${accent}`} onClick={onClick}><span className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></span><span className="metric-value">{value}</span><span className="metric-detail">{detail}<ArrowRight size={13} /></span></button>;
}

function ChatView({ token, conversations, activeConversation, messages, messageEvidence, loading, onCreateConversation, onSelectConversation, onMessages, onMessageEvidence, onRun, onNotice }: {
  token: string; conversations: Conversation[]; activeConversation: string | null; messages: Message[]; messageEvidence: Record<string, MessageEvidence>; loading: boolean;
  onCreateConversation: () => void; onSelectConversation: (id: string) => void; onMessages: (messages: Message[]) => void;
  onMessageEvidence: (messageId: string, evidence: MessageEvidence) => void;
  onRun: () => void; onNotice: (notice: Notice | null) => void;
}) {
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const active = conversations.find((item) => item.id === activeConversation);

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || !activeConversation || sending) return;
    setDraft("");
    setSending(true);
    onNotice(null);
    const temporary: Message = { id: `local-${Date.now()}`, conversation_id: activeConversation, role: "user", content, sequence: messages.length + 1, created_at: new Date().toISOString() };
    onMessages([...messages, temporary]);
    try {
      await apiRequest<Message>(`/conversations/${activeConversation}/messages`, token, { method: "POST", body: jsonBody({ role: "user", content }) });
      const result = await apiRequest<AgentResult>("/agent", token, { method: "POST", body: jsonBody({ request: content, conversation_id: activeConversation }) });
      const answer = result.response || result.errors.join(" ") || "The agent completed without a response.";
      const assistant: Message = { id: result.run_id ?? `assistant-${Date.now()}`, conversation_id: activeConversation, role: "assistant", content: answer, sequence: messages.length + 2, created_at: new Date().toISOString() };
      await apiRequest<Message>(`/conversations/${activeConversation}/messages`, token, { method: "POST", body: jsonBody({ role: "assistant", content: answer }) });
      onMessages([...messages, temporary, assistant]);
      onMessageEvidence(assistant.id, { retrieved_sources: result.retrieved_sources, tool_calls: result.tool_calls });
      onRun();
      if (result.status !== "completed") onNotice({ kind: "error", text: result.errors.join(" ") || "The agent run did not complete." });
    } catch (error) {
      onMessages([...messages, temporary]);
      onNotice({ kind: "error", text: humanError(error) });
    } finally {
      setSending(false);
    }
  }

  return <div className="chat-layout">
    <aside className="chat-history surface"><div className="section-heading"><div><p className="eyebrow">HISTORY</p><h2>Conversations</h2></div><button className="icon-button" aria-label="New conversation" title="New conversation" onClick={onCreateConversation}><Plus size={16} /></button></div>
      <button className="button button-outline button-wide new-chat-button" onClick={onCreateConversation}><Plus size={15} /> Start conversation</button>
      <div className="history-items">{conversations.map((conversation) => <button key={conversation.id} className={`history-item ${conversation.id === activeConversation ? "selected" : ""}`} onClick={() => onSelectConversation(conversation.id)}><MessageSquareText size={15} /><span>{conversation.title || "Untitled conversation"}</span><small>{dateLabel(conversation.updated_at)}</small></button>)}{!conversations.length && <p className="muted empty-inline">No conversation history yet.</p>}</div>
    </aside>
    <section className="chat-panel surface">
      <header className="chat-header"><div className="chat-agent-icon"><Sparkles size={17} /></div><div><strong>{active?.title || "AI operations assistant"}</strong><small><span className="online-dot" /> Knowledge and operations</small></div><button className="icon-button" title="Conversation options" aria-label="Conversation options"><MoreHorizontal size={18} /></button></header>
      <div className="chat-transcript">
        {!activeConversation ? <div className="chat-welcome"><span className="welcome-star"><Sparkles size={20} /></span><p className="eyebrow">AGENTOPS ASSISTANT</p><h2>Where should we begin?</h2><p>Ask about your organizational documents, or use a conversation to work through an operational request.</p><div className="suggestion-row"><button onClick={() => void createSuggestion("What guidance is available in our documents?")}>Search organizational knowledge <ArrowRight size={13} /></button><button onClick={() => void createSuggestion("Show me what I can do with tasks.")}>Explore operations <ArrowRight size={13} /></button></div></div>
          : messages.length ? messages.map((message) => <div key={message.id} className={`message-row ${message.role === "user" ? "message-user" : "message-assistant"}`}><span className={`message-avatar ${message.role === "user" ? "user-message-avatar" : "agent-message-avatar"}`}>{message.role === "user" ? <UserRound size={15} /> : <Bot size={16} />}</span><div className="message-body"><span className="message-author">{message.role === "user" ? "You" : "AgentOps"}<small>{new Intl.DateTimeFormat("en", { hour: "numeric", minute: "2-digit" }).format(new Date(message.created_at))}</small></span><p>{message.content}</p>{messageEvidence[message.id] && <MessageRunDetails evidence={messageEvidence[message.id]} />}</div></div>) : <div className="chat-welcome compact"><span className="welcome-star"><Sparkles size={18} /></span><h2>Ask your first question</h2><p>Answers use your accessible organizational knowledge and operational tools.</p></div>}
        {sending && <div className="message-row message-assistant"><span className="message-avatar agent-message-avatar"><Bot size={16} /></span><div className="message-body"><span className="message-author">AgentOps <small>working</small></span><p className="typing"><i /><i /><i /></p></div></div>}
      </div>
      {activeConversation ? <form className="composer" onSubmit={sendMessage}><button className="icon-button" type="button" title="Attach a document in Knowledge" aria-label="Open knowledge library"><Paperclip size={17} /></button><input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask a question or describe a task..." disabled={sending} aria-label="Message" /><span className="composer-hint">Enter to send</span><button className="send-button" disabled={!draft.trim() || sending} aria-label="Send message"><Send size={16} /></button></form> : <button className="button button-primary start-chat-cta" onClick={onCreateConversation}><Plus size={16} /> Start a conversation</button>}
      <div className="chat-disclaimer"><Shield size={12} /> Responses are grounded in accessible data. Verify important decisions.</div>
    </section>
  </div>;

  function createSuggestion(value: string) {
    setDraft(value);
    onCreateConversation();
  }
}

function MessageRunDetails({ evidence }: { evidence: MessageEvidence }) {
  return <div className="message-run-details">
    {evidence.retrieved_sources.length > 0 && <div className="message-sources"><strong><FileText size={13} /> Sources</strong>{evidence.retrieved_sources.map((source) => <details className="message-source" key={`${source.document_id}-${source.chunk_index}`}><summary>{source.filename} · chunk {source.chunk_index + 1}<span>{Math.round(source.score * 100)}%</span></summary><p>{source.content}</p></details>)}</div>}
    {evidence.tool_calls.length > 0 && <div className="message-tools"><strong><Settings2 size={13} /> Tool execution</strong>{evidence.tool_calls.map((toolCall, index) => {
      const toolName = typeof toolCall.tool_name === "string" ? toolCall.tool_name : "Platform tool";
      const succeeded = toolCall.success === true;
      const outcome = succeeded ? "Completed" : toolCall.success === false ? "Failed" : "Returned";
      const detail = toolCall.error ?? toolCall.result ?? toolCall.data;
      return <details className="message-tool" key={`${toolName}-${index}`}><summary><span>{toolName}</span><StatusPill status={outcome.toUpperCase()} /></summary>{detail !== undefined && <pre>{typeof detail === "string" ? detail : JSON.stringify(detail, null, 2)}</pre>}</details>;
    })}</div>}
  </div>;
}

function DocumentsView({ token, documents, searchResult, onSearchResult, onDocuments, onNotice }: { token: string; documents: DocumentRecord[]; searchResult: SearchResult | null; onSearchResult: (result: SearchResult | null) => void; onDocuments: (documents: DocumentRecord[]) => void; onNotice: (notice: Notice | null) => void }) {
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [filter, setFilter] = useState("ALL");
  const visible = documents.filter((document) => filter === "ALL" || document.status === filter);

  async function refresh() {
    const result = await apiRequest<DocumentRecord[]>("/documents?limit=100&offset=0", token);
    onDocuments(result);
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = new FormData(form).get("document");
    if (!(file instanceof File) || !file.size) {
      onNotice({ kind: "error", text: "Choose a non-empty PDF, TXT, or Markdown file." });
      return;
    }
    setUploading(true);
    onNotice(null);
    const data = new FormData();
    data.set("file", file);
    try {
      await apiRequest<DocumentRecord>("/documents", token, { method: "POST", body: data });
      form.reset();
      await refresh();
      onNotice({ kind: "success", text: `${file.name} is ready in your knowledge library.` });
    } catch (error) {
      onNotice({ kind: "error", text: humanError(error) });
    } finally {
      setUploading(false);
    }
  }

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    onNotice(null);
    try {
      onSearchResult(await apiRequest<SearchResult>("/documents/search", token, { method: "POST", body: jsonBody({ query, limit: 5 }) }));
    } catch (error) {
      onNotice({ kind: "error", text: humanError(error) });
    } finally {
      setSearching(false);
    }
  }

  async function archive(document: DocumentRecord) {
    if (!window.confirm(`Archive “${document.filename}”? It will no longer appear in search.`)) return;
    try {
      await apiRequest<void>(`/documents/${document.id}`, token, { method: "DELETE" });
      onDocuments(documents.filter((item) => item.id !== document.id));
      onNotice({ kind: "success", text: `${document.filename} was archived.` });
    } catch (error) {
      onNotice({ kind: "error", text: humanError(error) });
    }
  }

  return <div className="page-stack">
    <div className="page-heading heading-with-action"><div><p className="eyebrow">DOCUMENTS · ORGANIZATIONAL KNOWLEDGE</p><h1>Knowledge library</h1><p className="muted">Upload, search, and manage documents available to your organization.</p></div><span className="count-chip"><FileText size={14} /> {documents.length} files</span></div>
    <div className="documents-workspace">
      <div className="documents-main-column">
        <section className="surface upload-surface"><div className="section-heading"><div><p className="eyebrow">ADD KNOWLEDGE</p><h2>Upload a document</h2></div><span className="format-note">PDF · TXT · MD</span></div><form className="upload-form" onSubmit={upload}><label className="upload-drop"><input name="document" type="file" accept=".pdf,.txt,.md,.markdown,application/pdf,text/plain,text/markdown" /><span className="upload-icon"><Upload size={19} /></span><strong>Select a document</strong><small>PDF, TXT, or Markdown · up to 10 MB</small></label><button className="button button-primary" disabled={uploading}>{uploading ? <LoaderCircle className="spin" size={16} /> : <Upload size={16} />}{uploading ? "Uploading" : "Upload"}</button></form></section>
        <section className="surface library-surface"><div className="section-heading"><div><p className="eyebrow">YOUR LIBRARY</p><h2>Documents</h2></div><div className="filter-control"><Filter size={14} /><select value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Filter documents"><option value="ALL">All statuses</option><option value="READY">Ready</option><option value="PROCESSING">Processing</option><option value="FAILED">Failed</option></select><ChevronDown size={13} /></div></div>
          {visible.length ? <div className="table-wrap"><table><thead><tr><th>DOCUMENT</th><th>STATUS</th><th>SIZE</th><th>ADDED</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{visible.map((document) => <tr key={document.id}><td><div className="table-document"><span className="file-type">{document.file_extension.replace(".", "").slice(0, 4).toUpperCase()}</span><span><strong>{document.filename}</strong><small>{document.content_type}</small></span></div>{document.error_message && <small className="row-error">{document.error_message}</small>}</td><td><StatusPill status={document.status} /></td><td>{formatBytes(document.size_bytes)}</td><td>{dateLabel(document.created_at)}</td><td><button className="icon-button mini danger-hover" onClick={() => void archive(document)} title="Archive document" aria-label={`Archive ${document.filename}`}><Trash2 size={15} /></button></td></tr>)}</tbody></table></div> : <EmptyState title="No matching documents" copy="Upload a file to make it available in organizational search." action="Choose a file above" />}
        </section>
      </div>
      <aside className="surface search-surface"><div className="section-heading"><div><p className="eyebrow">RETRIEVAL</p><h2>Search knowledge</h2></div><span className="search-badge"><Search size={14} /></span></div><p className="muted small-copy">Search ready documents for relevant passages and sources.</p><form className="knowledge-search" onSubmit={search}><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="What do you need to know?" aria-label="Search organizational knowledge" /><button disabled={searching || !query.trim()} aria-label="Search">{searching ? <LoaderCircle size={16} className="spin" /> : <Search size={16} />}</button></form>
        {searchResult && <div className="search-results"><div className="search-result-summary">{searchResult.sources.length} sources found</div>{searchResult.limitation && <div className="limitation-note"><CircleAlert size={14} />{searchResult.limitation}</div>}{searchResult.sources.map((source) => <article className="source-card" key={`${source.document_id}-${source.chunk_index}`}><div className="source-card-head"><FileText size={14} /><strong>{source.filename}</strong><small>{Math.round(source.score * 100)}%</small></div><p>{source.content}</p><small>Chunk {source.chunk_index + 1}</small></article>)}</div>}
        {!searchResult && <div className="search-empty"><span><Sparkles size={18} /></span><strong>Evidence, not guesses.</strong><p>Search returns passages from documents your organization can access.</p></div>}
      </aside>
    </div>
  </div>;
}

function TasksView({ token, user, tasks, onTasks, detail, onDetail, onNotice }: { token: string; user: User; tasks: Task[]; onTasks: (tasks: Task[]) => void; detail: TaskDetail | null; onDetail: (detail: TaskDetail | null) => void; onNotice: (notice: Notice | null) => void }) {
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [assigneeFilter, setAssigneeFilter] = useState("ALL");
  const [query, setQuery] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [members, setMembers] = useState<User[]>([user]);
  const filtered = tasks.filter((task) => (statusFilter === "ALL" || task.status === statusFilter) && (assigneeFilter === "ALL" || task.assignee_id === assigneeFilter) && (!query || task.title.toLowerCase().includes(query.toLowerCase())));

  useEffect(() => {
    setMembers([user]);
    if (user.role !== "admin") return;
    apiRequest<User[]>("/users?limit=100&offset=0", token)
      .then(setMembers)
      .catch((error) => onNotice({ kind: "error", text: humanError(error) }));
  }, [token, user.id, user.role, onNotice]);

  function memberName(userId: string | null) {
    if (!userId) return "Unassigned";
    const member = members.find((item) => item.id === userId);
    return member ? `${member.username} (${member.email})` : `Member ${userId.slice(0, 8)}`;
  }

  async function refresh() {
    const params = new URLSearchParams({ limit: "100", offset: "0" });
    if (statusFilter !== "ALL") params.set("status", statusFilter);
    if (assigneeFilter && assigneeFilter !== "ALL") params.set("assignee_id", assigneeFilter);
    if (query) params.set("search", query);
    onTasks(await apiRequest<Task[]>(`/tasks?${params}`, token));
  }

  async function createTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    try {
      await apiRequest<Task>("/tasks", token, { method: "POST", body: jsonBody({ title: data.get("title"), description: data.get("description") || null, assignee_id: data.get("assignee_id") || null, priority: data.get("priority") || null, due_date: data.get("due_date") ? new Date(String(data.get("due_date"))).toISOString() : null }) });
      setShowCreate(false);
      await refresh();
      onNotice({ kind: "success", text: "Task created." });
    } catch (error) {
      onNotice({ kind: "error", text: humanError(error) });
    } finally {
      setBusy(false);
    }
  }

  async function updateStatus(task: Task, status: Task["status"]) {
    try {
      const updated = await apiRequest<Task>(`/tasks/${task.id}`, token, { method: "PATCH", body: jsonBody({ status }) });
      onTasks(tasks.map((item) => item.id === task.id ? updated : item));
      if (detail?.id === task.id) onDetail({ ...detail, status });
    } catch (error) {
      onNotice({ kind: "error", text: humanError(error) });
    }
  }

  async function updateAssignee(task: Task, assigneeId: string) {
    try {
      const updated = await apiRequest<Task>(`/tasks/${task.id}`, token, { method: "PATCH", body: jsonBody({ assignee_id: assigneeId || null }) });
      onTasks(tasks.map((item) => item.id === task.id ? updated : item));
      if (detail?.id === task.id) onDetail({ ...detail, assignee_id: updated.assignee_id });
    } catch (error) {
      onNotice({ kind: "error", text: humanError(error) });
    }
  }

  async function openDetail(task: Task) {
    try {
      onDetail(await apiRequest<TaskDetail>(`/tasks/${task.id}`, token));
    } catch (error) {
      onNotice({ kind: "error", text: humanError(error) });
    }
  }

  async function addComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail) return;
    const data = new FormData(event.currentTarget);
    try {
      await apiRequest(`/tasks/${detail.id}/comments`, token, { method: "POST", body: jsonBody({ content: data.get("comment") }) });
      event.currentTarget.reset();
      await openDetail(detail);
    } catch (error) {
      onNotice({ kind: "error", text: humanError(error) });
    }
  }

  async function archiveTask(task: Task) {
    if (!window.confirm(`Archive “${task.title}”?`)) return;
    try {
      await apiRequest<void>(`/tasks/${task.id}`, token, { method: "DELETE" });
      onTasks(tasks.filter((item) => item.id !== task.id));
      onDetail(null);
      onNotice({ kind: "success", text: "Task archived." });
    } catch (error) {
      onNotice({ kind: "error", text: humanError(error) });
    }
  }

  return <div className="page-stack">
    <div className="page-heading heading-with-action"><div><p className="eyebrow">OPERATIONS · TASK MANAGEMENT</p><h1>Task board</h1><p className="muted">Track organizational work and keep the next action clear.</p></div><button className="button button-primary" onClick={() => setShowCreate(true)}><Plus size={16} /> New task</button></div>
    <div className="task-toolbar surface"><label className="task-search"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tasks" aria-label="Search tasks" /></label><label className="filter-control"><Filter size={14} /><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="Filter by status"><option value="ALL">All statuses</option>{Object.entries(statusLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select><ChevronDown size={13} /></label><label className="filter-control"><UserRound size={14} /><select value={assigneeFilter} onChange={(event) => setAssigneeFilter(event.target.value)} aria-label="Filter by assignee"><option value="ALL">All assignees</option><option value="">Unassigned</option>{members.map((member) => <option key={member.id} value={member.id}>{member.username}</option>)}</select><ChevronDown size={13} /></label><span className="toolbar-count">{filtered.length} tasks</span></div>
    <div className="task-content-grid"><section className="surface task-table-surface">{filtered.length ? <div className="table-wrap"><table className="tasks-table"><thead><tr><th>TASK</th><th>STATUS</th><th>PRIORITY</th><th>ASSIGNEE</th><th>DUE DATE</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{filtered.map((task) => <tr key={task.id} className={detail?.id === task.id ? "row-selected" : ""}><td><button className="task-title-button" onClick={() => void openDetail(task)}><strong>{task.title}</strong><small>{task.description || "No description"}</small></button></td><td><select className={`status-select status-${task.status.toLowerCase()}`} value={task.status} onChange={(event) => void updateStatus(task, event.target.value as Task["status"])} aria-label={`Status for ${task.title}`}>{Object.entries(statusLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></td><td><span className={`priority-label ${(task.priority || "normal").toLowerCase()}`}>{task.priority || "Normal"}</span></td><td>{memberName(task.assignee_id)}</td><td>{dateLabel(task.due_date)}</td><td><button className="icon-button mini danger-hover" onClick={() => void archiveTask(task)} title="Archive task" aria-label={`Archive ${task.title}`}><Trash2 size={14} /></button></td></tr>)}</tbody></table></div> : <EmptyState title="No tasks found" copy="Create a task or adjust the current filters." action="Create task" onClick={() => setShowCreate(true)} />}</section>
      {detail && <aside className="surface task-detail"><div className="section-heading"><div><p className="eyebrow">TASK DETAILS</p><h2>Work item</h2></div><button className="icon-button mini" onClick={() => onDetail(null)} aria-label="Close task details"><X size={16} /></button></div><span className="detail-status"><StatusPill status={detail.status} /></span><h3>{detail.title}</h3><p className="detail-description">{detail.description || "No description provided."}</p><dl className="detail-meta"><div><dt>Priority</dt><dd>{detail.priority || "Normal"}</dd></div><div><dt>Due date</dt><dd>{dateLabel(detail.due_date)}</dd></div><div><dt>Assignee</dt><dd><select aria-label="Task assignee" value={detail.assignee_id || ""} onChange={(event) => void updateAssignee(detail, event.target.value)}><option value="">Unassigned</option>{members.map((member) => <option key={member.id} value={member.id}>{member.username}</option>)}</select><small className="assignee-description">{memberName(detail.assignee_id)}</small></dd></div></dl><div className="comments-block"><div className="section-heading"><h3>Comments</h3><span>{detail.comments.length}</span></div>{detail.comments.map((comment) => <div className="comment-item" key={comment.id}><span className="avatar avatar-tiny">{initials(comment.author_id)}</span><div><p>{comment.content}</p><small>{dateLabel(comment.created_at)}</small></div></div>)}<form className="comment-form" onSubmit={addComment}><input name="comment" required placeholder="Add a comment..." aria-label="Add comment" /><button className="icon-button mini" aria-label="Post comment"><Send size={15} /></button></form></div></aside>}
    </div>
    {showCreate && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowCreate(false); }}><section className="modal surface" role="dialog" aria-modal="true" aria-labelledby="create-task-title"><div className="section-heading"><div><p className="eyebrow">NEW WORK ITEM</p><h2 id="create-task-title">Create a task</h2></div><button className="icon-button" onClick={() => setShowCreate(false)} aria-label="Close"><X size={17} /></button></div><form className="create-task-form" onSubmit={createTask}><label>Title<input name="title" required maxLength={255} placeholder="What needs to be done?" /></label><label>Description<textarea name="description" rows={4} placeholder="Add useful context" /></label><label>Assignee<select name="assignee_id" defaultValue=""><option value="">Unassigned</option>{members.map((member) => <option key={member.id} value={member.id}>{member.username}{member.id === user.id ? " (you)" : ""}</option>)}</select></label><div className="form-two"><label>Priority<select name="priority"><option value="">Normal</option><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>URGENT</option></select></label><label>Due date<input name="due_date" type="date" /></label></div><button className="button button-primary button-wide" disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : <Plus size={16} />}Create task</button></form></section></div>}
  </div>;
}

function RunsView({ runs }: { runs: AgentRunRecord[] }) {
  return <div className="page-stack"><div className="page-heading"><p className="eyebrow">TRACEABILITY · PERSISTED EXECUTIONS</p><h1>Agent runs</h1><p className="muted">Review requests, outcomes, timing, node execution, sources, and tool calls.</p></div><section className="surface runs-surface">{runs.length ? runs.map((run) => <article className="run-card" key={run.run_id}><div className="run-card-heading"><span className={`run-icon ${run.status.toLowerCase() === "completed" ? "run-good" : "run-bad"}`}>{run.status.toLowerCase() === "completed" ? <CheckCircle2 size={16} /> : <CircleAlert size={16} />}</span><div><strong>{run.request}</strong><small>Started {new Date(run.started_at).toLocaleString()} · {run.run_id}</small></div><StatusPill status={run.status.toUpperCase()} /></div><div className="run-timing"><span><Clock3 size={13} />{run.duration_ms === null ? "Still running" : formatDuration(run.duration_ms)}</span>{run.completed_at && <span>Completed {new Date(run.completed_at).toLocaleString()}</span>}</div>{run.response && <p className="run-response">{run.response}</p>}{run.errors.map((error, errorIndex) => <p className="run-error" key={errorIndex}><CircleAlert size={14} />{error}</p>)}{run.nodes.length > 0 && <div className="run-node-list"><strong>Node execution</strong>{run.nodes.map((node) => <div className="run-node" key={`${node.sequence}-${node.node_name}`}><span className="run-node-sequence">{String(node.sequence).padStart(2, "0")}</span><span>{node.node_name}</span><StatusPill status={node.status.toUpperCase()} />{node.error_message && <small>{node.error_message}</small>}</div>)}</div>}{run.retrieved_sources.length > 0 && <div className="run-sources"><strong>Retrieved sources</strong>{run.retrieved_sources.map((source, index) => <span key={`${source.document_id}-${source.chunk_index}-${index}`}><FileText size={13} />{source.filename} · chunk {source.chunk_index + 1}</span>)}</div>}{run.tool_calls.length > 0 && <details className="tool-call-details"><summary><Settings2 size={14} /> {run.tool_calls.length} tool calls</summary><pre>{JSON.stringify(run.tool_calls, null, 2)}</pre></details>}</article>) : <EmptyState title="No persisted agent runs yet" copy="Runs appear after you submit a request in the AI workspace." action="Open AI workspace" />}</section><p className="inline-note"><Clock3 size={14} /> Runs are loaded from the authenticated, user-scoped history endpoint. Duration is calculated from the persisted start and completion timestamps.</p></div>;
}

function UsersView({
  token,
  currentUser,
  users,
  onUsers,
  onNotice,
}: {
  token: string;
  currentUser: User;
  users: User[];
  onUsers: (users: User[]) => void;
  onNotice: (notice: Notice | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const isAdmin = currentUser.role === "admin";

  const filtered = users.filter((u) => {
    const matchesQuery =
      !query ||
      u.username.toLowerCase().includes(query.toLowerCase()) ||
      u.email.toLowerCase().includes(query.toLowerCase()) ||
      (u.organization?.name && u.organization.name.toLowerCase().includes(query.toLowerCase()));
    const matchesRole = roleFilter === "ALL" || u.role.toLowerCase() === roleFilter.toLowerCase();
    const matchesStatus = statusFilter === "ALL" || (statusFilter === "active" ? u.is_active !== false : u.is_active === false);
    return matchesQuery && matchesRole && matchesStatus;
  });

  const activeCount = users.filter((u) => u.is_active !== false).length;
  const inactiveCount = users.filter((u) => u.is_active === false).length;

  async function toggleStatus(targetUser: User) {
    if (targetUser.id === currentUser.id) {
      onNotice({ kind: "error", text: "You cannot deactivate your own account." });
      return;
    }
    const nextStatus = !targetUser.is_active;
    const actionName = nextStatus ? "activate" : "deactivate";
    if (!window.confirm(`Are you sure you want to ${actionName} user "${targetUser.username}"?`)) return;

    setBusyId(targetUser.id);
    onNotice(null);
    try {
      const updated = await apiRequest<User>(`/users/${targetUser.id}/status`, token, {
        method: "PATCH",
        body: jsonBody({ is_active: nextStatus }),
      });
      onUsers(users.map((u) => (u.id === targetUser.id ? updated : u)));
      if (selectedUser?.id === targetUser.id) {
        setSelectedUser(updated);
      }
      onNotice({ kind: "success", text: `User ${targetUser.username} is now ${nextStatus ? "active" : "inactive"}.` });
    } catch (error) {
      onNotice({ kind: "error", text: humanError(error) });
    } finally {
      setBusyId(null);
    }
  }

  async function deleteUser(targetUser: User) {
    if (targetUser.id === currentUser.id) {
      onNotice({ kind: "error", text: "You cannot delete your own account." });
      return;
    }
    if (!window.confirm(`Are you sure you want to delete user "${targetUser.username}"? This action will deactivate and remove the user.`)) return;

    setBusyId(targetUser.id);
    onNotice(null);
    try {
      await apiRequest<void>(`/users/${targetUser.id}`, token, { method: "DELETE" });
      onUsers(users.filter((u) => u.id !== targetUser.id));
      if (selectedUser?.id === targetUser.id) {
        setSelectedUser(null);
      }
      onNotice({ kind: "success", text: `User ${targetUser.username} was deleted.` });
    } catch (error) {
      onNotice({ kind: "error", text: humanError(error) });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page-stack">
      <div className="page-heading heading-with-action">
        <div>
          <p className="eyebrow">{isAdmin ? "GLOBAL ADMINISTRATION · ALL REGISTERED USERS" : "ORGANIZATION DIRECTORY · TEAM MEMBERS"}</p>
          <h1>User management</h1>
          <p className="muted">
            {isAdmin
              ? "Manage registered users across all organizations, inspect account details, and enforce access controls."
              : "Manage organization members, review account details, and enforce access controls."}
          </p>
        </div>
        <span className="count-chip"><UserRound size={14} /> {isAdmin ? "Total Registered Users" : "Total Users"}: {users.length}</span>
      </div>

      <div className="metric-grid">
        <div className="metric-card metric-mint">
          <span className="metric-top"><span>{isAdmin ? "Registered Users" : "Total Members"}</span><span className="metric-icon"><UserRound size={17} /></span></span>
          <span className="metric-value">{users.length}</span>
          <span className="metric-detail">{isAdmin ? "Across all organizations" : "Organization users"}</span>
        </div>
        <div className="metric-card metric-amber">
          <span className="metric-top"><span>Active</span><span className="metric-icon"><UserCheck size={17} /></span></span>
          <span className="metric-value">{activeCount}</span>
          <span className="metric-detail">Able to sign in</span>
        </div>
        <div className="metric-card metric-coral">
          <span className="metric-top"><span>Inactive</span><span className="metric-icon"><UserX size={17} /></span></span>
          <span className="metric-value">{inactiveCount}</span>
          <span className="metric-detail">Access disabled</span>
        </div>
        <div className="metric-card metric-blue">
          <span className="metric-top"><span>{isAdmin ? "Global Scope" : "Organization"}</span><span className="metric-icon"><Shield size={17} /></span></span>
          <span className="metric-value" style={{ fontSize: "16px", marginTop: "12px", textTransform: "capitalize" }}>
            {isAdmin ? "All Organizations" : currentUser.organization?.name || "Workspace"}
          </span>
          <span className="metric-detail">{currentUser.role} role</span>
        </div>
      </div>

      <div className="task-toolbar surface">
        <label className="task-search">
          <Search size={16} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by name, email, or organization" aria-label="Search users" />
        </label>
        <label className="filter-control">
          <Filter size={14} />
          <select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)} aria-label="Filter by role">
            <option value="ALL">All roles</option>
            <option value="admin">Admin</option>
            <option value="supervisor">Supervisor</option>
            <option value="member">Member</option>
          </select>
          <ChevronDown size={13} />
        </label>
        <label className="filter-control">
          <ShieldCheck size={14} />
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="Filter by status">
            <option value="ALL">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <ChevronDown size={13} />
        </label>
        <span className="toolbar-count">{filtered.length} users</span>
      </div>

      <section className="surface task-table-surface">
        {filtered.length ? (
          <div className="table-wrap">
            <table className="tasks-table">
              <thead>
                <tr>
                  <th>NAME</th>
                  <th>EMAIL</th>
                  <th>ROLE</th>
                  <th>ORGANIZATION</th>
                  <th>STATUS</th>
                  <th>CREATED DATE</th>
                  <th><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((u) => {
                  const isSelf = u.id === currentUser.id;
                  const isActive = u.is_active !== false;
                  return (
                    <tr key={u.id} className={selectedUser?.id === u.id ? "row-selected" : ""}>
                      <td>
                        <button className="task-title-button" onClick={() => setSelectedUser(u)}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <span className="avatar avatar-tiny">{initials(u.username)}</span>
                            <strong>
                              {u.username}
                              {isSelf ? " (You)" : ""}
                            </strong>
                          </div>
                        </button>
                      </td>
                      <td>{u.email}</td>
                      <td>
                        <span className={`priority-label ${u.role === "admin" ? "urgent" : u.role === "supervisor" ? "medium" : "normal"}`}>
                          {u.role}
                        </span>
                      </td>
                      <td>
                        <span>{u.organization?.name || "—"}</span>
                      </td>
                      <td>
                        <span className={`status-pill ${isActive ? "pill-completed" : "pill-failed"}`}>
                          <span />
                          {isActive ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td>{dateLabel(u.created_at)}</td>
                      <td>
                        <div style={{ display: "flex", gap: "4px" }}>
                          <button
                            className="icon-button mini"
                            onClick={() => setSelectedUser(u)}
                            title="View account details"
                            aria-label={`View details for ${u.username}`}
                          >
                            <Eye size={14} />
                          </button>
                          <button
                            className={`icon-button mini ${isActive ? "danger-hover" : ""}`}
                            disabled={isSelf || busyId === u.id}
                            onClick={() => void toggleStatus(u)}
                            title={isSelf ? "Cannot change own status" : isActive ? "Deactivate user" : "Activate user"}
                            aria-label={isActive ? `Deactivate ${u.username}` : `Activate ${u.username}`}
                          >
                            {busyId === u.id ? <LoaderCircle size={14} className="spin" /> : isActive ? <UserX size={14} /> : <UserCheck size={14} />}
                          </button>
                          <button
                            className="icon-button mini danger-hover"
                            disabled={isSelf || busyId === u.id}
                            onClick={() => void deleteUser(u)}
                            title={isSelf ? "Cannot delete own account" : "Delete user"}
                            aria-label={`Delete ${u.username}`}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No users match the current filter"
            copy="Try adjusting the search query or role/status filters."
            action="Reset filters"
            onClick={() => { setQuery(""); setRoleFilter("ALL"); setStatusFilter("ALL"); }}
          />
        )}
      </section>

      {selectedUser && (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedUser(null); }}>
          <section className="modal surface" role="dialog" aria-modal="true" aria-labelledby="user-detail-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">ACCOUNT DETAILS</p>
                <h2 id="user-detail-title">{selectedUser.username}</h2>
              </div>
              <button className="icon-button" onClick={() => setSelectedUser(null)} aria-label="Close">
                <X size={17} />
              </button>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", margin: "16px 0 12px" }}>
              <span className="avatar" style={{ width: "42px", height: "42px", fontSize: "14px" }}>{initials(selectedUser.username)}</span>
              <div>
                <strong style={{ fontSize: "14px" }}>{selectedUser.username}{selectedUser.id === currentUser.id ? " (You)" : ""}</strong>
                <div style={{ display: "flex", gap: "6px", marginTop: "4px" }}>
                  <span className={`status-pill ${selectedUser.is_active !== false ? "pill-completed" : "pill-failed"}`}>
                    <span />
                    {selectedUser.is_active !== false ? "Active" : "Inactive"}
                  </span>
                  <span className="priority-label" style={{ textTransform: "capitalize" }}>{selectedUser.role}</span>
                </div>
              </div>
            </div>

            <dl className="detail-meta" style={{ marginTop: "16px", borderTop: "1px solid var(--line)", paddingTop: "14px" }}>
              <div>
                <dt>User ID</dt>
                <dd style={{ fontFamily: "monospace", fontSize: "11px" }}>{selectedUser.id}</dd>
              </div>
              <div>
                <dt>Email</dt>
                <dd>{selectedUser.email}</dd>
              </div>
              <div>
                <dt>Role</dt>
                <dd style={{ textTransform: "capitalize" }}>{selectedUser.role}</dd>
              </div>
              <div>
                <dt>Account Status</dt>
                <dd>{selectedUser.is_active !== false ? "Active (Can sign in)" : "Inactive (Access blocked)"}</dd>
              </div>
              <div>
                <dt>Organization</dt>
                <dd>{selectedUser.organization?.name || "Default Organization"} ({selectedUser.organization?.slug || "default"})</dd>
              </div>
              <div>
                <dt>Created Date</dt>
                <dd>{selectedUser.created_at ? new Date(selectedUser.created_at).toLocaleString() : "N/A"}</dd>
              </div>
              {selectedUser.updated_at && (
                <div>
                  <dt>Last Updated</dt>
                  <dd>{new Date(selectedUser.updated_at).toLocaleString()}</dd>
                </div>
              )}
            </dl>

            <div style={{ display: "flex", gap: "8px", marginTop: "18px", borderTop: "1px solid var(--line)", paddingTop: "14px", justifyContent: "flex-end" }}>
              {selectedUser.id !== currentUser.id && (
                <>
                  <button
                    className={`button ${selectedUser.is_active !== false ? "button-outline" : "button-primary"}`}
                    disabled={busyId === selectedUser.id}
                    onClick={() => void toggleStatus(selectedUser)}
                  >
                    {selectedUser.is_active !== false ? <UserX size={14} /> : <UserCheck size={14} />}
                    {selectedUser.is_active !== false ? "Deactivate User" : "Activate User"}
                  </button>
                  <button
                    className="button button-outline"
                    style={{ color: "var(--danger)", borderColor: "var(--danger)" }}
                    disabled={busyId === selectedUser.id}
                    onClick={() => void deleteUser(selectedUser)}
                  >
                    <Trash2 size={14} />
                    Delete
                  </button>
                </>
              )}
              <button className="button button-outline" onClick={() => setSelectedUser(null)}>
                Close
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function TaskRow({ task, onClick }: { task: Task; onClick: () => void }) {
  return <button className="overview-task-row" onClick={onClick}><span className={`task-status-dot dot-${task.status.toLowerCase()}`} /><span className="overview-task-title"><strong>{task.title}</strong><small>{task.priority || "Normal priority"}</small></span><span className="task-due">{dateLabel(task.due_date)}</span><ArrowRight size={14} /></button>;
}

function StatusPill({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  return <span className={`status-pill pill-${normalized}`}><span />{statusLabels[status] || status.replaceAll("_", " ")}</span>;
}

function EmptyState({ title, copy, action, onClick }: { title: string; copy: string; action?: string; onClick?: () => void }) {
  return <div className="empty-state"><span className="empty-mark"><Sparkles size={17} /></span><strong>{title}</strong><p>{copy}</p>{action && onClick && <button className="text-button" onClick={onClick}>{action} <ArrowRight size={14} /></button>}</div>;
}

function LoadingRows() {
  return <div className="loading-rows" aria-label="Loading"><i /><i /><i /></div>;
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(milliseconds: number) {
  if (milliseconds < 1000) return `${milliseconds} ms`;
  return `${(milliseconds / 1000).toFixed(1)} s`;
}