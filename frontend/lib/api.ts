export type ApiErrorBody = {
  error?: { code?: string; message?: string };
};

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export async function apiRequest<T>(
  path: string,
  token?: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError("The AgentOps API could not be reached.", 0, "NETWORK_ERROR");
  }

  if (!response.ok) {
    if (response.status === 401 && token && typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("agentops:unauthorized", { detail: { token } }));
    }
    const payload = (await response.json().catch(() => ({}))) as ApiErrorBody;
    const defaultMessage = response.status === 500
      ? "The backend server is unreachable or an internal error occurred. Please ensure the backend is running on port 8000."
      : `Request failed (${response.status}).`;
    throw new ApiError(
      payload.error?.message ?? defaultMessage,
      response.status,
      payload.error?.code,
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export type User = {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  organization_id: string | null;
  created_at?: string;
  updated_at?: string;
  organization?: {
    id: string;
    name: string;
    slug: string;
    is_active: boolean;
  } | null;
};

export type UserStats = {
  total: number;
  active_count: number;
  inactive_count: number;
};

export type TokenResponse = { access_token: string; user: User; expires_in: number };
export type Conversation = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};
export type Message = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sequence: number;
  created_at: string;
};
export type DocumentRecord = {
  id: string;
  filename: string;
  content_type: string;
  file_extension: string;
  size_bytes: number;
  status: string;
  error_message: string | null;
  metadata_json: Record<string, string>;
  created_at?: string;
};
export type SearchResult = {
  context: string;
  limitation: string | null;
  sources: Array<{
    document_id: string;
    filename: string;
    chunk_index: number;
    content: string;
    score: number;
  }>;
};
export type Task = {
  id: string;
  title: string;
  description: string | null;
  status: "TODO" | "IN_PROGRESS" | "BLOCKED" | "COMPLETED" | "CANCELLED";
  priority: string | null;
  assignee_id: string | null;
  due_date: string | null;
  updated_at: string;
};
export type TaskComment = { id: string; content: string; author_id: string; created_at: string };
export type TaskDetail = Task & { comments: TaskComment[] };
export type AgentResult = {
  run_id: string | null;
  status: string;
  response: string | null;
  errors: string[];
  retrieved_sources: SearchResult["sources"];
  tool_calls: Array<Record<string, unknown>>;
};
export type AgentRunRecord = AgentResult & {
  run_id: string;
  conversation_id: string | null;
  request: string;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  nodes: Array<{
    sequence: number;
    node_name: string;
    status: string;
    error_message: string | null;
  }>;
};

export const jsonBody = (value: unknown) => JSON.stringify(value);
