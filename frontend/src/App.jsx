import React, { useState, useEffect, useRef, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Send,
  Mic,
  Square,
  Upload,
  Trash2,
  Volume2,
  VolumeX,
  Bell,
  FolderOpen,
  Loader2,
  Bot,
  User,
  Sparkles,
  Moon,
  Sun,
  Check,
  FileText,
  Settings,
  Plug,
  Smartphone,
  Lock,
  Unlock,
  X,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";
const API_TOKEN_KEY = "pai-api-token";

// Keep the private bootstrap token out of the JavaScript bundle. Public
// deployments should replace this local token with an OIDC/JWT flow.
function getApiToken() {
  try {
    return localStorage.getItem(API_TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

function authHeaders(extra = {}) {
  const token = getApiToken();
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

const ROLE_OPTIONS = [
  ["employee", "General employee", "Shared company information"],
  ["sales", "Sales", "Sales and shared information"],
  ["hr", "HR", "People operations and HR"],
  ["finance", "Finance", "Finance and approved reports"],
  ["manager", "Manager", "Department and manager-level data"],
  ["executive", "Executive", "Executive and strategic data"],
  ["admin", "Administrator", "Full RAG administration"],
];

function LoginPage({ darkMode, setDarkMode, redirectTo = "/" }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const login = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await apiPost("/auth/login", { username: username.trim(), password });
      localStorage.setItem(API_TOKEN_KEY, result.token);
      window.location.href = redirectTo;
    } catch (e) {
      setError(e.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  const demo = async (profile) => {
    const credentials = {
      employee: ["employee", "EmployeeDemo!2026"],
      sales: ["sales", "SalesDemo!2026"],
      admin: ["admin", "AdminDemo!2026"],
    }[profile];
    setBusy(true);
    setError("");
    try {
      const result = await apiPost("/auth/login", { username: credentials[0], password: credentials[1] });
      localStorage.setItem(API_TOKEN_KEY, result.token);
      window.location.href = profile === "admin" ? "/admin" : redirectTo;
    } catch (e) {
      setError(e.message || "Demo login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F7F5F1] dark:bg-[#17161A] text-[#201F1D] dark:text-[#EDEAE3] px-4">
      <div className="fixed top-5 right-5 flex gap-2">
        <button onClick={() => setDarkMode((value) => !value)} className="px-3 py-2 rounded-lg border border-[#D9D3C8] dark:border-[#4A4650] text-sm dark:text-[#EDEAE3]">{darkMode ? "Light" : "Dark"}</button>
        <a href="/" className="px-3 py-2 rounded-lg border border-[#D9D3C8] dark:border-[#4A4650] text-sm dark:text-[#EDEAE3]">Home</a>
      </div>
      <div className="w-full max-w-md rounded-2xl border border-[#E4E0D8] dark:border-[#322F35] bg-white/80 dark:bg-[#211F24] p-8 shadow-xl">
        <p className="text-xs uppercase tracking-[0.2em] text-[#8A8578] dark:text-[#B8B1A7]">Private RAG</p>
        <h1 className="text-3xl font-semibold mt-3">Sign in to Company AI</h1>
        <p className="text-sm text-[#777268] dark:text-[#B8B1A7] mt-2">Your role controls which company documents and actions are available.</p>
        <form onSubmit={login} className="mt-7 space-y-3">
          <input required value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" autoComplete="username" className="w-full px-4 py-3 rounded-lg border border-[#D9D3C8] dark:border-[#4A4650] bg-transparent dark:bg-[#17161A] dark:text-[#EDEAE3] dark:placeholder:text-[#9B9488]" />
          <input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" autoComplete="current-password" className="w-full px-4 py-3 rounded-lg border border-[#D9D3C8] dark:border-[#4A4650] bg-transparent dark:bg-[#17161A] dark:text-[#EDEAE3] dark:placeholder:text-[#9B9488]" />
          <button disabled={busy} className="w-full px-4 py-3 rounded-lg bg-[#5B4B8A] text-white disabled:opacity-50">{busy ? "Signing in..." : "Sign in"}</button>
        </form>
        {error && <p className="mt-4 p-3 rounded-lg bg-[#FCE9E7] dark:bg-[#3A2426] text-sm text-[#B0473F] dark:text-[#F4A7A0]">{error}</p>}
      </div>
    </div>
  );
}

function LoadingScreen() {
  return <div className="min-h-screen flex items-center justify-center bg-[#F7F5F1] dark:bg-[#17161A] text-[#777268] dark:text-[#B8B1A7] text-sm">Checking secure session...</div>;
}

async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const error = new Error(err.detail || `GET ${path} failed (${res.status})`);
    error.status = res.status;
    throw error;
  }
  return res.json();
}
async function apiPost(path, body, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
    signal: options.signal,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `POST ${path} failed`);
  }
  return res.json();
}
async function apiPatch(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `PATCH ${path} failed`);
  }
  return res.json();
}
async function apiDelete(path) {
  const res = await fetch(`${API_BASE}${path}`, { method: "DELETE", headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `DELETE ${path} failed`);
  }
  return res.json();
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [status, setStatus] = useState({ mode: "company", provider: "", model: "", available_providers: [], demo_mode: false });
  const [apiToken, setApiToken] = useState(() => getApiToken());
  const [tokenDraft, setTokenDraft] = useState(() => getApiToken());
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [authState, setAuthState] = useState("checking");

  const [categories, setCategories] = useState([]);
  const [uploadCategory, setUploadCategory] = useState("General");
  const [newCategoryMode, setNewCategoryMode] = useState(false);
  const [filterCategory, setFilterCategory] = useState("All");
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [documents, setDocuments] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [users, setUsers] = useState([]);
  const [userForm, setUserForm] = useState({ username: "", display_name: "", password: "", role: "employee", department: "" });

  const [reminders, setReminders] = useState([]);
  const [pendingActions, setPendingActions] = useState([]);
  const [voiceReplyEnabled, setVoiceReplyEnabled] = useState(false);
  const [forcePrivate, setForcePrivate] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);

  const [darkMode, setDarkMode] = useState(() => {
    try {
      return localStorage.getItem("pai-theme") === "dark";
    } catch {
      return false;
    }
  });

  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioPlayerRef = useRef(null);
  const chatAbortRef = useRef(null);

  // ---------- Dark mode ----------
  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    try {
      localStorage.setItem("pai-theme", darkMode ? "dark" : "light");
    } catch {
      /* ignore storage errors */
    }
  }, [darkMode]);

  // ---------- Initial load ----------
  useEffect(() => {
    apiGet("/status").then(setStatus).catch(() => {});
    apiGet("/history").then(setMessages).catch(() => {});
    refreshCategories();
    refreshDocuments();
    refreshSubmissions();
    refreshReminders();
    refreshPendingActions();
    const timer = window.setInterval(() => {
      refreshCategories();
      refreshDocuments();
      refreshSubmissions();
      refreshReminders();
      refreshPendingActions();
    }, 10000);
    return () => window.clearInterval(timer);
  }, []);

  // The assistant and admin panel are private routes. A public status check is
  // useful for bootstrapping the UI, but a protected endpoint is required to
  // establish that this browser actually has a valid session/token.
  useEffect(() => {
    if (window.location.pathname === "/login") {
      setAuthState("anonymous");
      return;
    }
    if (!getApiToken()) {
      setAuthState("anonymous");
      return;
    }
    const isAdminRoute = window.location.pathname === "/admin" || window.location.pathname === "/admin/users";
    apiGet(isAdminRoute ? "/admin/users" : "/history")
      .then(() => setAuthState(isAdminRoute ? "admin" : "authenticated"))
      .catch((error) => {
        if (error.status === 401 || error.status === 403) {
          try { localStorage.removeItem(API_TOKEN_KEY); } catch { /* ignore storage errors */ }
          setAuthState("anonymous");
        } else {
          // A temporary 502/backend restart must not log a signed-in user out.
          setAuthState(isAdminRoute ? "admin" : "authenticated");
        }
      });
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  const refreshCategories = () => {
    apiGet("/documents/categories")
      .then((d) => setCategories(d.categories || []))
      .catch(() => {});
  };

  const refreshDocuments = () => {
    apiGet("/documents/list")
      .then((d) => setDocuments(d.documents || []))
      .catch(() => {});
  };

  const refreshSubmissions = () => {
    apiGet("/document-submissions?include_completed=true")
      .then((d) => setSubmissions(d.submissions || []))
      .catch(() => {});
  };

  const refreshReminders = () => {
    apiGet("/reminders/list")
      .then((d) => setReminders(d.reminders || []))
      .catch(() => {});
  };

  const refreshPendingActions = () => {
    apiGet("/actions/pending")
      .then((d) => setPendingActions(d.actions || []))
      .catch(() => {});
  };

  const demoLogin = async (profile) => {
    try {
      const credentials = {
        employee: ["employee", "EmployeeDemo!2026"],
        sales: ["sales", "SalesDemo!2026"],
        admin: ["admin", "AdminDemo!2026"],
      }[profile];
      const result = await apiPost("/auth/login", { username: credentials[0], password: credentials[1] });
      localStorage.setItem(API_TOKEN_KEY, result.token);
      window.location.reload();
    } catch (error) {
      setUploadMsg(error.message || "Demo login failed");
    }
  };

  const loginUser = async (event) => {
    event.preventDefault();
    try {
      const result = await apiPost("/auth/login", { username: loginUsername, password: loginPassword });
      localStorage.setItem(API_TOKEN_KEY, result.token);
      window.location.reload();
    } catch (error) {
      setUploadMsg(error.message || "Login failed");
    }
  };

  // ---------- Sending a message ----------
  const sendMessage = useCallback(
    async (text) => {
      const question = (text ?? input).trim();
      if (!question) return;

      setMessages((prev) => [...prev, { role: "user", content: question }]);
      setInput("");
      setThinking(true);
      const controller = new AbortController();
      chatAbortRef.current = controller;

      try {
        const category = filterCategory === "All" ? null : filterCategory;
        const data = await apiPost("/chat", { question, category, force_private: forcePrivate }, { signal: controller.signal });
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.answer,
            source: data.source,
            sources: data.sources || [],
          },
        ]);
        refreshReminders();

        if (voiceReplyEnabled) {
          playSpeech(data.answer);
        }
      } catch (e) {
        if (e.name === "AbortError") return;
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${e.message}` },
        ]);
      } finally {
        if (chatAbortRef.current === controller) chatAbortRef.current = null;
        setThinking(false);
      }
    },
    [input, filterCategory, voiceReplyEnabled, forcePrivate]
  );

  const stopGenerating = () => {
    chatAbortRef.current?.abort();
    chatAbortRef.current = null;
    setThinking(false);
  };

  const playSpeech = async (text) => {
    try {
      const res = await fetch(`${API_BASE}/voice/speak`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ text }),
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      if (audioPlayerRef.current) {
        audioPlayerRef.current.src = url;
        audioPlayerRef.current.play();
      }
    } catch {
      /* silently ignore playback errors */
    }
  };

  // ---------- Voice input (mic) ----------
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
      recorder.onstop = handleRecordingStop;
      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      alert("Microphone access nahi mil paya. Browser permissions check karo.");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  };

  const handleRecordingStop = async () => {
    setTranscribing(true);
    try {
      const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
      const formData = new FormData();
      formData.append("audio", blob, "recording.webm");

      const res = await fetch(`${API_BASE}/voice/transcribe`, {
        method: "POST",
        headers: authHeaders(),
        body: formData,
      });
      const data = await res.json();
      if (data.text && !data.text.startsWith("(")) {
        sendMessage(data.text);
      }
    } catch {
      /* ignore */
    } finally {
      setTranscribing(false);
    }
  };

  // ---------- Document upload ----------
  const handleUpload = async () => {
    const files = fileInputRef.current?.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setUploadMsg("");
    const formData = new FormData();
    for (const f of files) formData.append("files", f);
    formData.append("category", uploadCategory);

    try {
      const res = await fetch(`${API_BASE}/documents/upload`, {
        method: "POST",
        headers: authHeaders(),
        body: formData,
      });
      const data = await res.json();
      setUploadMsg(data.status === "pending_approval"
        ? "Submitted for administrator approval. It is not searchable yet."
        : `${data.chunks_added} chunks added under "${uploadCategory}"`);
      refreshCategories();
      refreshDocuments();
      refreshSubmissions();
      fileInputRef.current.value = "";
    } catch (e) {
      setUploadMsg(`Upload failed: ${e.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDocument = async (filename, category) => {
    try {
      await fetch(
        `${API_BASE}/documents/${encodeURIComponent(filename)}?category=${encodeURIComponent(category)}`,
        { method: "DELETE", headers: authHeaders() }
      );
      refreshDocuments();
      refreshCategories();
    } catch {
      /* ignore */
    }
  };

  const handleClearHistory = async () => {
    await fetch(`${API_BASE}/history`, { method: "DELETE", headers: authHeaders() });
    setMessages([]);
  };

  // ---------- Reminders ----------
  const handleMarkDone = async (id) => {
    await fetch(`${API_BASE}/reminders/${id}/done`, { method: "PATCH", headers: authHeaders() });
    refreshReminders();
  };

  const handleDeleteReminder = async (id) => {
    await fetch(`${API_BASE}/reminders/${id}`, { method: "DELETE", headers: authHeaders() });
    refreshReminders();
  };

  const reviewAction = async (id, decision) => {
    try {
      await apiPost(`/actions/${id}/${decision}`, {});
      refreshPendingActions();
    } catch (e) {
      alert(e.message);
    }
  };

  // ---------- Provider switch ----------
  const handleProviderChange = async (provider) => {
    try {
      const data = await apiPost("/settings/provider", { provider });
      setStatus((prev) => ({ ...prev, provider: data.provider, model: data.model }));
    } catch (e) {
      alert(e.message);
    }
  };

  const saveApiToken = () => {
    const value = tokenDraft.trim();
    try {
      if (value) localStorage.setItem(API_TOKEN_KEY, value);
      else localStorage.removeItem(API_TOKEN_KEY);
    } catch {
      /* ignore storage errors */
    }
    setApiToken(value);
    window.location.reload();
  };

  const signOut = () => {
    try { localStorage.removeItem(API_TOKEN_KEY); } catch { /* ignore storage errors */ }
    window.location.href = "/login";
  };

  // Keep this after all App hooks and callbacks are initialized. Returning
  // earlier would leave the initial-load effect with TDZ references.
  if (window.location.pathname === "/admin") {
    if (authState === "checking") return <LoadingScreen />;
    if (authState !== "admin") return <LoginPage darkMode={darkMode} setDarkMode={setDarkMode} redirectTo="/admin" />;
    return <RagAdminPanel />;
  }
  if (window.location.pathname === "/admin/users") {
    if (authState === "checking") return <LoadingScreen />;
    if (authState !== "admin") return <LoginPage darkMode={darkMode} setDarkMode={setDarkMode} redirectTo="/admin/users" />;
    return <RoleManagementPage />;
  }
  if (window.location.pathname === "/login") {
    return <LoginPage darkMode={darkMode} setDarkMode={setDarkMode} />;
  }
  if (authState === "checking") return <LoadingScreen />;
  if (authState !== "authenticated") return <LoginPage darkMode={darkMode} setDarkMode={setDarkMode} />;

  return (
    <div className="h-screen w-screen flex bg-[#F7F5F1] dark:bg-[#17161A] text-[#201F1D] dark:text-[#EDEAE3] overflow-hidden transition-colors">
      {/* ================= SIDEBAR ================= */}
      <aside className="w-80 shrink-0 border-r border-[#E4E0D8] dark:border-[#322F35] flex flex-col overflow-y-auto">
        <div className="px-6 pt-6 pb-4 flex items-start justify-between">
          <div>
            <h1
              className="text-2xl text-[#3D3A34] dark:text-[#F3F1EA] leading-tight"
              style={{ fontFamily: "'Fraunces', serif" }}
            >
              {status.mode === "company" ? "Company AI" : "Personal AI"}
            </h1>
            <p className="text-sm text-[#8A8578] dark:text-[#9B9488] mt-1">
              {status.provider ? `${status.provider.toUpperCase()} · ${status.model}` : "Connecting..."}
            </p>
            <button onClick={signOut} className="inline-block ml-3 mt-2 text-xs text-[#B0473F] dark:text-[#F4A7A0] hover:underline">Sign out</button>
          </div>
          <button
            onClick={() => setDarkMode((v) => !v)}
            title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
            className="shrink-0 w-9 h-9 rounded-full flex items-center justify-center bg-[#EDE9FE] dark:bg-[#2A2730] text-[#5B4B8A] dark:text-[#C4B5FD] hover:opacity-80 transition-opacity"
          >
            {darkMode ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>

        {false && <>
        {/* Documents */}
        <section className="px-6 py-4 border-t border-[#E4E0D8] dark:border-[#322F35]">
          <div className="flex items-center gap-2 text-sm font-medium text-[#3D3A34] dark:text-[#F3F1EA] mb-3">
            <FolderOpen size={16} />
            Documents
          </div>

          {!newCategoryMode ? (
            <select
              value={uploadCategory}
              onChange={(e) => {
                if (e.target.value === "__new__") {
                  setNewCategoryMode(true);
                  setUploadCategory("");
                } else {
                  setUploadCategory(e.target.value);
                }
              }}
              className="w-full text-sm border border-[#E4E0D8] dark:border-[#3A3740] rounded-md px-3 py-2 bg-white dark:bg-[#211F24] text-[#201F1D] dark:text-[#EDEAE3] mb-3 focus:outline-none focus:ring-2 focus:ring-[#5B4B8A]/40"
            >
              <option value="General">General</option>
              {categories
                .filter((c) => c !== "General")
                .map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              <option value="__new__">+ New category</option>
            </select>
          ) : (
            <input
              autoFocus
              placeholder="New category name"
              value={uploadCategory}
              onChange={(e) => setUploadCategory(e.target.value)}
              onBlur={() => !uploadCategory && setNewCategoryMode(false)}
              className="w-full text-sm border border-[#E4E0D8] dark:border-[#3A3740] rounded-md px-3 py-2 bg-white dark:bg-[#211F24] text-[#201F1D] dark:text-[#EDEAE3] mb-3 focus:outline-none focus:ring-2 focus:ring-[#5B4B8A]/40"
            />
          )}

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.csv"
            className="w-full text-xs text-[#8A8578] dark:text-[#9B9488] mb-3 file:mr-2 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:bg-[#EDE9FE] dark:file:bg-[#2A2730] file:text-[#5B4B8A] dark:file:text-[#C4B5FD] file:cursor-pointer"
          />

          <button
            onClick={handleUpload}
            disabled={uploading}
            className="w-full flex items-center justify-center gap-2 bg-[#5B4B8A] hover:bg-[#4C3D77] text-white text-sm py-2 rounded-md transition-colors disabled:opacity-50"
          >
            {uploading ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} />}
            Process Documents
          </button>

          {uploadMsg && <p className="text-xs text-[#7A9E7E] mt-2">{uploadMsg}</p>}

          {documents.length > 0 && (
            <div className="mt-4 space-y-1.5 max-h-40 overflow-y-auto">
              {documents.map((doc) => (
                <div
                  key={`${doc.filename}-${doc.category}`}
                  className="flex items-center justify-between gap-2 text-xs bg-[#F1EFEA] dark:bg-[#211F24] rounded-md px-2.5 py-1.5"
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    <FileText size={13} className="shrink-0 text-[#8A8578] dark:text-[#9B9488]" />
                    <span className="truncate text-[#3D3A34] dark:text-[#EDEAE3]" title={doc.filename}>
                      {doc.filename}
                    </span>
                    <span className="shrink-0 text-[#8A8578] dark:text-[#9B9488]">· {doc.category}</span>
                  </div>
                  <button
                    onClick={() => handleDeleteDocument(doc.filename, doc.category)}
                    className="shrink-0 text-[#B0473F] hover:opacity-70"
                    title="Delete document"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Search filter */}
        <section className="px-6 py-4 border-t border-[#E4E0D8] dark:border-[#322F35]">
          <label className="text-sm font-medium text-[#3D3A34] dark:text-[#F3F1EA] block mb-2">
            Search within category
          </label>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="w-full text-sm border border-[#E4E0D8] dark:border-[#3A3740] rounded-md px-3 py-2 bg-white dark:bg-[#211F24] text-[#201F1D] dark:text-[#EDEAE3] focus:outline-none focus:ring-2 focus:ring-[#5B4B8A]/40"
          >
            <option value="All">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </section>

        </>}

        <section className="px-6 py-4 border-t border-[#E4E0D8] dark:border-[#322F35]">
          <div className="flex items-center gap-2 text-sm font-medium text-[#3D3A34] dark:text-[#F3F1EA] mb-2">
            <Lock size={15} /> Submit company data for review
          </div>
          <p className="text-xs text-[#8A8578] dark:text-[#9B9488] mb-3">
            Employee uploads stay quarantined until an administrator approves them.
          </p>
          <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt,.csv" className="w-full text-xs mb-3" />
          <button onClick={handleUpload} disabled={uploading} className="w-full bg-[#5B4B8A] text-white text-sm py-2 rounded-md disabled:opacity-50">
            {uploading ? "Submitting…" : "Submit for admin approval"}
          </button>
          {submissions.length > 0 && <div className="mt-3 space-y-1">
            {submissions.slice(0, 5).map((item) => <p key={item.id} className="text-xs text-[#777268] dark:text-[#B8B1A7] truncate">{item.filename} · {item.status}</p>)}
          </div>}
          {uploadMsg && <p className="text-xs text-[#7A9E7E] mt-2">{uploadMsg}</p>}
        </section>

        {/* Reminders */}
        <section className="px-6 py-4 border-t border-[#E4E0D8] dark:border-[#322F35]">
          <div className="flex items-center gap-2 text-sm font-medium text-[#3D3A34] dark:text-[#F3F1EA] mb-3">
            <Bell size={16} />
            Reminders
          </div>

          {reminders.length === 0 ? (
            <p className="text-xs text-[#8A8578] dark:text-[#9B9488]">No reminders yet.</p>
          ) : (
            <div className="space-y-1.5">
              {reminders.map((r) => (
                <div
                  key={r.id}
                  className="flex items-start gap-2 text-xs bg-[#F1EFEA] dark:bg-[#211F24] rounded-md px-2.5 py-2"
                >
                  <button
                    onClick={() => !r.done && handleMarkDone(r.id)}
                    className={`shrink-0 w-4 h-4 mt-0.5 rounded border flex items-center justify-center ${
                      r.done
                        ? "bg-[#7A9E7E] border-[#7A9E7E] text-white"
                        : "border-[#C7C2B6] dark:border-[#4A4650]"
                    }`}
                    title={r.done ? "Done" : "Mark as done"}
                  >
                    {r.done && <Check size={11} />}
                  </button>
                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-[#3D3A34] dark:text-[#EDEAE3] ${
                        r.done ? "line-through opacity-50" : ""
                      }`}
                    >
                      {r.text}
                    </p>
                    <p className="text-[#8A8578] dark:text-[#9B9488] mt-0.5">{r.remind_at}</p>
                  </div>
                  <button
                    onClick={() => handleDeleteReminder(r.id)}
                    className="shrink-0 text-[#B0473F] hover:opacity-70"
                    title="Delete reminder"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Approval queue: admins can approve external side effects. */}
        {pendingActions.length > 0 && (
          <section className="px-6 py-4 border-t border-[#E4E0D8] dark:border-[#322F35]">
            <div className="flex items-center gap-2 text-sm font-medium text-[#3D3A34] dark:text-[#F3F1EA] mb-3">
              <Lock size={16} />
              Pending approvals
            </div>
            <div className="space-y-2">
              {pendingActions.map((action) => (
                <div key={action.id} className="text-xs bg-[#F1EFEA] dark:bg-[#211F24] rounded-md px-2.5 py-2">
                  <p className="font-medium text-[#3D3A34] dark:text-[#EDEAE3]">{action.action_type} #{action.id}</p>
                  {action.payload?.to_email && <p className="text-[#8A8578] dark:text-[#B8B1A7] truncate">To: {action.payload.to_email}</p>}
                  <div className="flex gap-2 mt-2">
                    <button onClick={() => reviewAction(action.id, "approve")} className="text-[#4F7A54] hover:underline">Approve</button>
                    <button onClick={() => reviewAction(action.id, "reject")} className="text-[#B0473F] hover:underline">Reject</button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Settings */}
        <section className="px-6 py-4 border-t border-[#E4E0D8] dark:border-[#322F35] mt-auto">
          <div className="flex items-center gap-2 text-sm font-medium text-[#3D3A34] dark:text-[#F3F1EA] mb-3">
            <Settings size={16} />
            Settings
          </div>

          {false && <>
          <label className="block text-xs text-[#8A8578] dark:text-[#9B9488] mb-1">
            Private API token
          </label>
          <div className="flex gap-2 mb-3">
            <input
              type="password"
              value={tokenDraft}
              onChange={(e) => setTokenDraft(e.target.value)}
              placeholder={apiToken ? "Token saved" : "Paste deploy/secrets/api_auth_token"}
              className="min-w-0 flex-1 text-xs border border-[#E4E0D8] dark:border-[#3A3740] rounded-md px-2.5 py-2 bg-white dark:bg-[#211F24] text-[#201F1D] dark:text-[#EDEAE3]"
              autoComplete="off"
            />
            <button
              onClick={saveApiToken}
              className="shrink-0 text-xs px-2.5 rounded-md bg-[#5B4B8A] text-white hover:bg-[#4C3D77]"
            >
              Save
            </button>
          </div>

          {status.available_providers && status.available_providers.length > 1 && (
            <select
              value={status.provider}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="w-full text-sm border border-[#E4E0D8] dark:border-[#3A3740] rounded-md px-3 py-2 bg-white dark:bg-[#211F24] text-[#201F1D] dark:text-[#EDEAE3] mb-3 focus:outline-none focus:ring-2 focus:ring-[#5B4B8A]/40"
            >
              {status.available_providers.map((p) => (
                <option key={p} value={p}>
                  {p.toUpperCase()}
                </option>
              ))}
            </select>
          )}

          </>}

          <label className="flex items-center justify-between text-sm text-[#3D3A34] dark:text-[#EDEAE3] cursor-pointer">
            <span className="flex items-center gap-2">
              {voiceReplyEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
              Speak replies
            </span>
            <input
              type="checkbox"
              checked={voiceReplyEnabled}
              onChange={(e) => setVoiceReplyEnabled(e.target.checked)}
              className="accent-[#5B4B8A]"
            />
          </label>

          <button
            onClick={handleClearHistory}
            className="w-full flex items-center justify-center gap-2 text-sm text-[#B0473F] hover:bg-[#FBEAE8] dark:hover:bg-[#2A1F1E] py-2 rounded-md transition-colors mt-4"
          >
            <Trash2 size={14} />
            Clear chat history
          </button>

        </section>
      </aside>

      {/* ================= CHAT PANEL ================= */}
      <main className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-y-auto px-8 py-8">
          {messages.length === 0 && !thinking && (
            <div className="h-full flex flex-col items-center justify-center text-center text-[#8A8578] dark:text-[#9B9488]">
              <Sparkles size={28} className="mb-3 text-[#5B4B8A] dark:text-[#C4B5FD]" />
              <p
                className="text-lg text-[#3D3A34] dark:text-[#F3F1EA]"
                style={{ fontFamily: "'Fraunces', serif" }}
              >
                Ask anything — in your language
              </p>
              <p className="text-sm mt-1 max-w-sm">
                {status.mode === "company"
                  ? "Search and analyze your private company data. Answers stay within authorized sources."
                  : "Upload documents on the left, then ask questions."}
                English, Hindi, or Gujarati — the assistant replies in kind.
              </p>
            </div>
          )}

          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((m, i) => (
              <ChatBubble key={i} message={m} />
            ))}

            {thinking && (
              <div className="flex items-center gap-3 text-[#8A8578] dark:text-[#9B9488] text-sm">
                <Bot size={18} />
                <Loader2 size={14} className="animate-spin" />
                Thinking...
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        </div>

        {/* Input bar */}
        <div className="border-t border-[#E4E0D8] dark:border-[#322F35] px-8 py-5">
          {forcePrivate && (
            <div className="max-w-3xl mx-auto mb-2 flex items-center gap-1.5 text-xs text-[#7A9E7E]">
              <Lock size={12} />
              Private Mode on — is baar ka sawal hamesha Ollama (local) se jayega
            </div>
          )}
          <div className="max-w-3xl mx-auto flex items-end gap-3">
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Ask me anything..."
              className="flex-1 resize-none border border-[#E4E0D8] dark:border-[#3A3740] rounded-xl px-4 py-3 text-sm bg-white dark:bg-[#211F24] text-[#201F1D] dark:text-[#EDEAE3] focus:outline-none focus:ring-2 focus:ring-[#5B4B8A]/40 max-h-40"
            />

            <button
              onClick={() => setForcePrivate((v) => !v)}
              title={
                forcePrivate
                  ? "Private Mode ON - click to allow Groq/cloud again"
                  : "Force this chat to use local Ollama only (Private Mode)"
              }
              className={`shrink-0 w-11 h-11 rounded-xl flex items-center justify-center transition-colors ${
                forcePrivate
                  ? "bg-[#7A9E7E] text-white"
                  : "bg-[#EDE9FE] dark:bg-[#2A2730] text-[#5B4B8A] dark:text-[#C4B5FD] hover:bg-[#DDD6FE] dark:hover:bg-[#332F3C]"
              }`}
            >
              {forcePrivate ? <Lock size={17} /> : <Unlock size={17} />}
            </button>

            <button
              onClick={recording ? stopRecording : startRecording}
              disabled={transcribing}
              title={recording ? "Stop recording" : "Record a question"}
              className={`shrink-0 w-11 h-11 rounded-xl flex items-center justify-center transition-colors ${
                recording
                  ? "bg-[#B0473F] text-white"
                  : "bg-[#EDE9FE] dark:bg-[#2A2730] text-[#5B4B8A] dark:text-[#C4B5FD] hover:bg-[#DDD6FE] dark:hover:bg-[#332F3C]"
              }`}
            >
              {transcribing ? (
                <Loader2 size={18} className="animate-spin" />
              ) : recording ? (
                <Square size={16} />
              ) : (
                <Mic size={18} />
              )}
            </button>

            <button
              onClick={thinking ? stopGenerating : () => sendMessage()}
              disabled={!thinking && !input.trim()}
              title={thinking ? "Stop generating" : "Send message"}
              className="shrink-0 w-11 h-11 rounded-xl flex items-center justify-center bg-[#5B4B8A] text-white hover:bg-[#4C3D77] transition-colors disabled:opacity-40"
            >
              {thinking ? <Square size={17} /> : <Send size={18} />}
            </button>
          </div>
        </div>
      </main>

      <audio ref={audioPlayerRef} className="hidden" />
    </div>
  );
}

function ChatBubble({ message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser
            ? "bg-[#5B4B8A] text-white"
            : "bg-[#EDE9FE] dark:bg-[#2A2730] text-[#5B4B8A] dark:text-[#C4B5FD]"
        }`}
      >
        {isUser ? <User size={15} /> : <Bot size={15} />}
      </div>
      <div className={`max-w-[80%] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        <div
          className={`rounded-2xl px-4 py-3 text-[15px] leading-relaxed ${
            isUser
              ? "bg-[#5B4B8A] text-white rounded-tr-sm whitespace-pre-wrap"
              : "bg-white dark:bg-[#211F24] border border-[#E4E0D8] dark:border-[#322F35] text-[#201F1D] dark:text-[#EDEAE3] rounded-tl-sm markdown-body"
          }`}
        >
          {isUser ? (
            message.content
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          )}
        </div>

        {!isUser && message.source && (
          <div className="flex items-center gap-1.5 mt-1.5 px-1">
            {message.source.toLowerCase().includes("local") ? (
              <span className="inline-flex items-center gap-1 text-[11px] bg-[#E8F1E9] dark:bg-[#1B2A1E] text-[#4F7A54] dark:text-[#8FC498] rounded-full px-2 py-0.5 font-medium">
                <Lock size={10} />
                Private · Local Model
              </span>
            ) : message.source.toLowerCase().includes("ollama") ? (
              <span className="inline-flex items-center gap-1 text-[11px] bg-[#E8F1E9] dark:bg-[#1B2A1E] text-[#4F7A54] dark:text-[#8FC498] rounded-full px-2 py-0.5 font-medium">
                <Lock size={10} />
                Private · Ollama
              </span>
            ) : message.source.toLowerCase().includes("groq") ||
              message.source.toLowerCase().includes("openai") ||
              message.source.toLowerCase().includes("anthropic") ? (
              <span className="inline-flex items-center gap-1 text-[11px] bg-[#F1EFEA] dark:bg-[#211F24] text-[#5A564C] dark:text-[#9B9488] rounded-full px-2 py-0.5">
                <Unlock size={10} />
                {message.source}
              </span>
            ) : (
              <span className="text-[11px] text-[#8A8578] dark:text-[#9B9488]">
                {message.source}
              </span>
            )}
          </div>
        )}

        {message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1.5 px-1">
            {message.sources.map((s, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 text-[11px] bg-[#F1EFEA] dark:bg-[#211F24] text-[#5A564C] dark:text-[#9B9488] rounded-full px-2 py-0.5"
              >
                <FileText size={10} />
                {s.file}
                {s.page ? ` · p.${s.page}` : ""}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ConnectionRow({ icon, name, state, ready, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-2 py-1.5 text-left text-xs hover:bg-[#F1EFEA] dark:hover:bg-[#211F24] rounded-md px-1"
    >
      <span className={ready ? "text-[#4F7A54]" : "text-[#8A8578]"}>{icon}</span>
      <span className="flex-1 truncate">{name}</span>
      <span className={ready ? "text-[#4F7A54]" : "text-[#8A8578]"}>{state}</span>
    </button>
  );
}

function RoleManagementPage() {
  const [users, setUsers] = useState([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [userForm, setUserForm] = useState({ username: "", display_name: "", password: "", role: "employee", department: "" });

  const refresh = useCallback(() => {
    apiGet("/admin/users")
      .then((data) => setUsers(data.users || []))
      .catch((error) => setMessage(error.message || "Unable to load users."));
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 10000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const createUser = async (event) => {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const payload = {
        username: userForm.username,
        display_name: userForm.display_name,
        password: userForm.password || null,
        roles: [userForm.role],
        departments: userForm.department ? [userForm.department] : [],
      };
      if (editingId) await apiPatch(`/admin/users/${editingId}`, payload);
      else await apiPost("/admin/users", { ...payload, password: userForm.password });
      setMessage(`User ${userForm.username} ${editingId ? "updated" : "created"} successfully.`);
      setEditingId(null);
      setUserForm({ username: "", display_name: "", password: "", role: "employee", department: "" });
      refresh();
    } catch (error) {
      setMessage(error.message || "User creation failed.");
    } finally {
      setBusy(false);
    }
  };

  const editUser = (user) => {
    setEditingId(user.id);
    setUserForm({ username: user.username, display_name: user.display_name, password: "", role: user.roles[0] || "employee", department: user.departments[0] || "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const toggleUser = async (user) => {
    try {
      await apiPost(`/admin/users/${user.id}/enabled?enabled=${!user.enabled}`, {});
      setMessage(`${user.username} ${user.enabled ? "disabled" : "enabled"}.`);
      refresh();
    } catch (error) { setMessage(error.message || "Account status update failed."); }
  };

  const removeUser = async (user) => {
    if (!window.confirm(`Remove ${user.username}? This revokes sessions and cannot be undone.`)) return;
    try {
      await apiDelete(`/admin/users/${user.id}`);
      setMessage(`${user.username} removed.`);
      refresh();
    } catch (error) { setMessage(error.message || "User removal failed."); }
  };

  const signOut = () => {
    try { localStorage.removeItem(API_TOKEN_KEY); } catch { /* ignore storage errors */ }
    window.location.href = "/login";
  };

  return (
    <div className="min-h-screen bg-[#F7F5F1] dark:bg-[#17161A] text-[#201F1D] dark:text-[#EDEAE3] p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-8">
          <div><p className="text-xs uppercase tracking-[0.2em] text-[#8A8578] dark:text-[#B8B1A7]">Private RAG</p><h1 className="text-3xl font-semibold mt-2">Roles & users</h1><p className="text-sm text-[#777268] dark:text-[#B8B1A7] mt-2">Create accounts with least-privilege role and department access.</p></div>
          <div className="flex gap-2"><a href="/admin" className="px-4 py-2 rounded-lg border border-[#D9D3C8] dark:border-[#4A4650] text-sm dark:text-[#EDEAE3]">Back to admin</a><button onClick={signOut} className="px-4 py-2 rounded-lg border border-[#C9B8B4] text-sm text-[#B0473F] dark:text-[#F4A7A0]">Sign out</button></div>
        </div>
        {message && <div className="mb-5 p-3 rounded-lg bg-[#EEEAF7] dark:bg-[#2A2738] text-sm text-[#5B4B8A] dark:text-[#C4B5FD]">{message}</div>}

        <section className="rounded-xl border border-[#E4E0D8] dark:border-[#322F35] p-5 mb-8 bg-white/50 dark:bg-[#211F24]">
          <h2 className="font-medium">Available roles</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2 mt-4">{ROLE_OPTIONS.map(([value, label, description]) => <div key={value} title={description} className="rounded-lg border border-[#E4E0D8] dark:border-[#4A4650] bg-[#F7F5F1] dark:bg-[#17161A] px-3 py-3"><p className="text-sm font-medium">{label}</p><p className="text-[11px] text-[#777268] dark:text-[#B8B1A7] mt-1">{description}</p></div>)}</div>
        </section>

        <section className="rounded-xl border border-[#E4E0D8] dark:border-[#322F35] p-5 mb-8 bg-white/50 dark:bg-[#211F24]">
          <h2 className="font-medium">{editingId ? "Edit user and role access" : "Add role-based user"}</h2>
          <p className="text-xs text-[#777268] dark:text-[#B8B1A7] mt-1 mb-4">Passwords are hashed and never displayed again. Leave password blank while editing to keep the current password.</p>
          <form onSubmit={createUser} className="grid md:grid-cols-2 lg:grid-cols-5 gap-3">
            <input required placeholder="Username" value={userForm.username} onChange={(e) => setUserForm({ ...userForm, username: e.target.value })} className="px-3 py-2 rounded-md border border-[#D9D3C8] dark:border-[#4A4650] bg-transparent dark:bg-[#17161A] text-sm dark:text-[#EDEAE3] dark:placeholder:text-[#9B9488]" />
            <input required placeholder="Display name" value={userForm.display_name} onChange={(e) => setUserForm({ ...userForm, display_name: e.target.value })} className="px-3 py-2 rounded-md border border-[#D9D3C8] dark:border-[#4A4650] bg-transparent dark:bg-[#17161A] text-sm dark:text-[#EDEAE3] dark:placeholder:text-[#9B9488]" />
            <input required={!editingId} minLength={10} type="password" placeholder={editingId ? "New password (optional)" : "Temporary password"} value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} className="px-3 py-2 rounded-md border border-[#D9D3C8] dark:border-[#4A4650] bg-transparent dark:bg-[#17161A] text-sm dark:text-[#EDEAE3] dark:placeholder:text-[#9B9488]" />
            <select value={userForm.role} onChange={(e) => setUserForm({ ...userForm, role: e.target.value })} className="px-3 py-2 rounded-md border border-[#D9D3C8] dark:border-[#4A4650] bg-transparent dark:bg-[#17161A] text-sm dark:text-[#EDEAE3]">{ROLE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label} ({value})</option>)}</select>
            <div className="flex gap-2"><input placeholder="Department (optional)" value={userForm.department} onChange={(e) => setUserForm({ ...userForm, department: e.target.value })} className="min-w-0 flex-1 px-3 py-2 rounded-md border border-[#D9D3C8] dark:border-[#4A4650] bg-transparent dark:bg-[#17161A] text-sm dark:text-[#EDEAE3] dark:placeholder:text-[#9B9488]" /><button disabled={busy} className="px-4 py-2 rounded-md bg-[#5B4B8A] text-white text-sm disabled:opacity-50">{busy ? "Saving..." : editingId ? "Save changes" : "Create"}</button>{editingId && <button type="button" onClick={() => { setEditingId(null); setUserForm({ username: "", display_name: "", password: "", role: "employee", department: "" }); }} className="px-3 py-2 rounded-md border border-[#D9D3C8] dark:border-[#4A4650] text-sm">Cancel</button>}</div>
          </form>
        </section>

        <section className="rounded-xl border border-[#E4E0D8] dark:border-[#322F35] p-5 bg-white/50 dark:bg-[#211F24]">
          <div className="flex items-center justify-between"><h2 className="font-medium">Current users</h2><button onClick={refresh} className="text-sm text-[#5B4B8A] dark:text-[#C4B5FD]">Refresh</button></div>
          <div className="mt-4 space-y-2">{users.map((user) => <div key={user.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-[#E4E0D8] dark:border-[#4A4650] px-4 py-3"><div className="min-w-0 flex-1"><p className="font-medium">{user.display_name} <span className="text-xs font-normal text-[#777268] dark:text-[#B8B1A7]">@{user.username}</span></p><p className="text-xs text-[#777268] dark:text-[#B8B1A7] mt-1">Role: {user.roles.join(", ")} · Department: {user.departments.join(", ") || "company-wide"} · {user.enabled ? "active" : "disabled"}</p></div><button onClick={() => editUser(user)} className="text-xs text-[#5B4B8A] dark:text-[#C4B5FD]">Edit</button><button onClick={() => toggleUser(user)} className="text-xs text-[#B0473F] dark:text-[#F4A7A0]">{user.enabled ? "Disable" : "Enable"}</button><button onClick={() => removeUser(user)} className="text-xs text-[#B0473F] dark:text-[#F4A7A0]">Remove</button></div>)}</div>
        </section>
      </div>
    </div>
  );
}

function RagAdminPanel() {
  const [connections, setConnections] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [users, setUsers] = useState([]);
  const [userForm, setUserForm] = useState({ username: "", display_name: "", password: "", role: "employee", department: "" });
  const [sources, setSources] = useState([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [category, setCategory] = useState("Company Server");
  const [uploadRole, setUploadRole] = useState("shared");
  const [uploadDepartment, setUploadDepartment] = useState("");
  const [file, setFile] = useState(null);
  const [tokenDraft, setTokenDraft] = useState(() => getApiToken());
  const [adminLoginUsername, setAdminLoginUsername] = useState("");
  const [adminLoginPassword, setAdminLoginPassword] = useState("");
  const [llmStatus, setLlmStatus] = useState({ provider: "", model: "", available_providers: [] });

  const saveAdminToken = () => {
    const value = tokenDraft.trim();
    if (value) localStorage.setItem(API_TOKEN_KEY, value);
    else localStorage.removeItem(API_TOKEN_KEY);
    window.location.reload();
  };

  const signOut = () => {
    try { localStorage.removeItem(API_TOKEN_KEY); } catch { /* ignore storage errors */ }
    window.location.href = "/login";
  };

  const loginAdmin = async (event) => {
    event.preventDefault();
    try {
      const result = await apiPost("/auth/login", {
        username: adminLoginUsername.trim(),
        password: adminLoginPassword,
      });
      localStorage.setItem(API_TOKEN_KEY, result.token);
      window.location.reload();
    } catch (error) {
      setMessage(error.message || "Admin login failed.");
    }
  };

  const refresh = useCallback(() => {
    Promise.all([
      apiGet("/status"),
      apiGet("/admin/connections"),
      apiGet("/admin/data-sources"),
      apiGet("/documents/list"),
      apiGet("/document-submissions"),
      apiGet("/admin/users"),
    ])
      .then(([statusData, connectionData, sourceData, documentData, submissionData, userData]) => {
        setLlmStatus(statusData);
        setConnections(connectionData);
        setSources(sourceData.sources || []);
        setDocuments(documentData.documents || []);
        setSubmissions(submissionData.submissions || []);
        setUsers(userData.users || []);
        setMessage("");
      })
      .catch((error) => setMessage(error.message || "Admin access required."));
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 10000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const switchProvider = async (provider) => {
    try {
      const result = await apiPost("/settings/provider", { provider });
      setLlmStatus((current) => ({ ...current, provider: result.provider, model: result.model }));
      setMessage(`Provider switched to ${result.provider}. Private document policy remains active.`);
    } catch (error) {
      setMessage(error.message || "Provider switch failed.");
    }
  };

  const setDataServer = async (enabled) => {
    setBusy(true);
    try {
      const result = await apiPost("/admin/data-server", { enabled });
      setMessage(enabled ? "Company data server connected." : `Disconnected. ${result.indexed_chunks_removed} indexed chunks removed.`);
      refresh();
    } catch (error) {
      setMessage(error.message || "Data server operation failed.");
    } finally {
      setBusy(false);
    }
  };

  const sync = async () => {
    setBusy(true);
    try {
      const result = await apiPost("/connectors/filesystem/sync", {});
      setMessage(`Sync complete: ${result.files_seen} files and ${result.chunks_added} chunks.`);
      refresh();
    } catch (error) {
      setMessage(error.message || "Sync failed.");
    } finally {
      setBusy(false);
    }
  };

  const upload = async (event) => {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    try {
      const form = new FormData();
      form.append("files", file);
      form.append("category", category || "General");
      form.append("required_role", uploadRole || "shared");
      form.append("department", uploadDepartment.trim().toLowerCase());
      const response = await fetch(`${API_BASE}/documents/upload`, {
        method: "POST", headers: authHeaders(), body: form,
      });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "Upload failed");
      const result = await response.json();
      setFile(null);
      setMessage(`${result.filename} added with ${result.chunks_added} chunks.`);
      refresh();
    } catch (error) {
      setMessage(error.message || "Upload failed.");
    } finally {
      setBusy(false);
    }
  };

  const reviewSubmission = async (id, decision) => {
    setBusy(true);
    try {
      await apiPost(`/document-submissions/${id}/${decision}`, { note: "Reviewed in admin panel" });
      setMessage(`Submission ${decision}.`);
      refresh();
    } catch (error) {
      setMessage(error.message || "Review failed.");
    } finally {
      setBusy(false);
    }
  };

  const downloadSubmission = async (item) => {
    try {
      const response = await fetch(`${API_BASE}/document-submissions/${item.id}/download`, { headers: authHeaders() });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "Download failed");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = item.filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setMessage(error.message || "Download failed.");
    }
  };

  const createUser = async (event) => {
    event.preventDefault();
    try {
      await apiPost("/admin/users", {
        username: userForm.username,
        display_name: userForm.display_name,
        password: userForm.password,
        roles: [userForm.role],
        departments: userForm.department ? [userForm.department] : [],
      });
      setMessage(`User ${userForm.username} created.`);
      setUserForm({ username: "", display_name: "", password: "", role: "employee", department: "" });
      refresh();
    } catch (error) {
      setMessage(error.message || "User creation failed.");
    }
  };

  const remove = async (document) => {
    if (!window.confirm(`Remove ${document.filename} from the RAG index? Source files are not deleted.`)) return;
    setBusy(true);
    try {
      await apiDelete(`/documents/${encodeURIComponent(document.filename)}?category=${encodeURIComponent(document.category)}`);
      setMessage(`${document.filename} removed from the RAG index.`);
      refresh();
    } catch (error) {
      setMessage(error.message || "Remove failed.");
    } finally {
      setBusy(false);
    }
  };

  const server = connections?.data_server;
  return (
    <div className="min-h-screen bg-[#F7F5F1] dark:bg-[#17161A] text-[#201F1D] dark:text-[#EDEAE3] p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[#8A8578] dark:text-[#B8B1A7]">Private RAG</p>
            <h1 className="text-3xl font-semibold mt-2">RAG Admin Panel</h1>
            <p className="text-sm text-[#777268] dark:text-[#B8B1A7] mt-2">Manage company sources, indexing and documents.</p>
          </div>
          <div className="flex gap-2">
            <button onClick={refresh} className="px-4 py-2 rounded-lg border border-[#D9D3C8] dark:border-[#4A4650] text-sm dark:text-[#EDEAE3]">Refresh</button>
            <a href="/admin/users" className="px-4 py-2 rounded-lg bg-[#5B4B8A] text-white text-sm">Add role / user</a>
            <button onClick={signOut} className="px-4 py-2 rounded-lg border border-[#C9B8B4] text-sm text-[#B0473F] dark:text-[#F4A7A0]">Sign out</button>
            <a href="/" className="px-4 py-2 rounded-lg bg-[#5B4B8A] text-white text-sm">Open assistant</a>
          </div>
        </div>

        {message && <div className="mb-5 p-3 rounded-lg bg-[#EEEAF7] text-sm text-[#5B4B8A]">{message}</div>}

        <section className="rounded-xl border border-[#E4E0D8] dark:border-[#322F35] p-5 mb-8 bg-white/50 dark:bg-[#211F24]">
          <h2 className="font-medium">Model provider</h2>
          <p className="text-xs text-[#777268] dark:text-[#B8B1A7] mt-1 mb-3">Admin login is already active for this panel. Sign out from the top-right controls.</p>
          <div className="max-w-xl">
            <label className="text-xs text-[#777268] dark:text-[#B8B1A7]">LLM provider</label>
            <select value={llmStatus.provider} onChange={(e) => switchProvider(e.target.value)} className="mt-1 w-full px-3 py-2 rounded-md border border-[#D9D3C8] dark:border-[#4A4650] bg-transparent dark:bg-[#17161A] text-sm dark:text-[#EDEAE3]">
              {(llmStatus.available_providers || []).map((provider) => <option key={provider} value={provider}>{provider.toUpperCase()}</option>)}
            </select>
            <p className="text-[11px] text-[#777268] dark:text-[#B8B1A7] mt-1">Groq is used only for non-document questions. Retrieved company documents remain local while cloud document context is disabled.</p>
          </div>
        </section>

        <section className="grid md:grid-cols-3 gap-4 mb-8">
          <div className="md:col-span-2 rounded-xl border border-[#E4E0D8] dark:border-[#322F35] p-5 bg-white/50 dark:bg-[#211F24]">
            <h2 className="font-medium">Company data server</h2>
            <p className="text-xs text-[#777268] dark:text-[#B8B1A7] mt-1">Mounted source: read-only. Disconnect removes its indexed chunks but never deletes source files.</p>
            <div className="flex items-center gap-3 mt-5">
              <span className={`text-sm ${server?.configured ? "text-[#4F7A54]" : "text-[#8A8578] dark:text-[#B8B1A7]"}`}>
                {server?.configured ? "Connected read-only" : server?.mounted ? "Disconnected" : "Not configured"}
              </span>
              <button disabled={busy || !server?.mounted || server?.configured} onClick={() => setDataServer(true)} className="px-3 py-1.5 rounded-md bg-[#5B4B8A] text-white text-xs disabled:opacity-40">Connect</button>
              <button disabled={busy || !server?.configured} onClick={() => setDataServer(false)} className="px-3 py-1.5 rounded-md border border-[#C9B8B4] text-xs disabled:opacity-40">Disconnect</button>
              <button disabled={busy || !server?.configured} onClick={sync} className="px-3 py-1.5 rounded-md border border-[#D9D3C8] dark:border-[#4A4650] dark:text-[#EDEAE3] text-xs disabled:opacity-40">Sync now</button>
            </div>
          </div>
          <div className="rounded-xl border border-[#E4E0D8] dark:border-[#322F35] p-5 bg-white/50 dark:bg-[#211F24]">
            <h2 className="font-medium">Indexed documents</h2>
            <p className="text-4xl font-semibold mt-3">{documents.length}</p>
            <p className="text-xs text-[#777268] dark:text-[#B8B1A7] mt-1">Visible to the current admin tenant</p>
          </div>
        </section>

        <section className="rounded-xl border border-[#E4E0D8] dark:border-[#322F35] p-5 mb-8 bg-white/50 dark:bg-[#211F24]">
          <h2 className="font-medium">Employee upload approvals</h2>
          <p className="text-xs text-[#777268] dark:text-[#B8B1A7] mt-1 mb-4">Pending files are quarantined and cannot be searched until approved.</p>
          {submissions.length === 0 ? <p className="text-sm text-[#777268] dark:text-[#B8B1A7]">No pending submissions.</p> : <div className="space-y-2">
            {submissions.map((item) => <div key={item.id} className="flex flex-wrap items-center gap-3 border border-[#E4E0D8] rounded-lg p-3 text-sm">
              <div className="min-w-0 flex-1"><p className="font-medium truncate">{item.filename}</p><p className="text-xs text-[#777268] dark:text-[#B8B1A7]">{item.category} · {item.required_role} · {item.department_id || "company-wide"} · by {item.user_id}</p></div>
              <button disabled={busy} onClick={() => downloadSubmission(item)} className="px-3 py-1.5 rounded-md border border-[#D9D3C8] dark:border-[#4A4650] dark:text-[#EDEAE3] text-xs">Download</button>
              <button disabled={busy} onClick={() => reviewSubmission(item.id, "approve")} className="px-3 py-1.5 rounded-md bg-[#4F7A54] text-white text-xs">Approve</button>
              <button disabled={busy} onClick={() => reviewSubmission(item.id, "reject")} className="px-3 py-1.5 rounded-md border border-[#C9B8B4] text-xs">Reject</button>
            </div>)}
          </div>}
        </section>

        <section className="rounded-xl border border-[#E4E0D8] dark:border-[#322F35] p-5 mb-8 bg-white/50 dark:bg-[#211F24]">
          <h2 className="font-medium mb-1">Add data to RAG</h2>
          <p className="text-xs text-[#777268] dark:text-[#B8B1A7] mb-4">Upload PDF, DOCX, TXT or CSV. Uploads are indexed into the selected category.</p>
          <form onSubmit={upload} className="flex flex-wrap gap-3 items-center">
            <input type="file" accept=".pdf,.docx,.txt,.csv" onChange={(e) => setFile(e.target.files?.[0] || null)} className="text-sm" />
            <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Category" className="px-3 py-2 rounded-md border border-[#D9D3C8] dark:border-[#4A4650] bg-transparent dark:bg-[#17161A] text-sm dark:text-[#EDEAE3] dark:placeholder:text-[#9B9488]" />
            <select value={uploadRole} onChange={(e) => setUploadRole(e.target.value)} className="px-3 py-2 rounded-md border border-[#D9D3C8] dark:border-[#4A4650] bg-transparent dark:bg-[#17161A] text-sm dark:text-[#EDEAE3]"><option value="shared">Shared</option>{ROLE_OPTIONS.filter(([value]) => value !== "admin").map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
            <input value={uploadDepartment} onChange={(e) => setUploadDepartment(e.target.value)} placeholder="Department (optional)" className="px-3 py-2 rounded-md border border-[#D9D3C8] dark:border-[#4A4650] bg-transparent dark:bg-[#17161A] text-sm dark:text-[#EDEAE3] dark:placeholder:text-[#9B9488]" />
            <button disabled={busy || !file} className="px-4 py-2 rounded-md bg-[#5B4B8A] text-white text-sm disabled:opacity-40">Add and index</button>
          </form>
        </section>

        <section className="rounded-xl border border-[#E4E0D8] dark:border-[#322F35] overflow-hidden bg-white/50 dark:bg-[#211F24]">
          <div className="p-5 border-b border-[#E4E0D8] dark:border-[#322F35]"><h2 className="font-medium">RAG index</h2></div>
          {documents.length === 0 ? <p className="p-5 text-sm text-[#777268] dark:text-[#B8B1A7]">No indexed documents.</p> : documents.map((document) => (
            <div key={`${document.filename}-${document.category}`} className="flex items-center gap-3 px-5 py-3 border-b border-[#E4E0D8] dark:border-[#322F35] last:border-0">
              <FolderOpen size={15} className="text-[#8A8578] dark:text-[#B8B1A7]" />
              <span className="flex-1 text-sm truncate">{document.filename}</span>
              <span className="text-xs text-[#8A8578] dark:text-[#B8B1A7]">{document.category} · {document.chunks} chunks</span>
              <button onClick={() => remove(document)} disabled={busy} className="text-xs text-[#B0473F] disabled:opacity-40">Remove</button>
            </div>
          ))}
        </section>

        <section className="mt-8 rounded-xl border border-[#E4E0D8] dark:border-[#322F35] p-5 bg-white/50 dark:bg-[#211F24]">
          <h2 className="font-medium mb-3">Available connection types</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2 text-xs text-[#777268] dark:text-[#B8B1A7]">
            {sources.map((source) => <div key={source.key} className="p-2 rounded-md border border-[#E4E0D8] dark:border-[#322F35]">{source.name}</div>)}
          </div>
        </section>
      </div>
    </div>
  );
}
