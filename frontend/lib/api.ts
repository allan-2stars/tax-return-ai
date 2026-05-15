/**
 * API client — ALL fetch() calls to the FastAPI backend live here.
 * Never call fetch() directly from components or pages.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

// ── Types ────────────────────────────────────────────────────────────────────

export interface Session {
  id: string;
  title: string;
  financial_year: string;
  status: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  session_id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number | null;
  file_hash: string | null;
  category: string | null;
  financial_year: string;
  status: string;
  created_at: string;
}

export interface UploadResponse {
  document_id: string;
  job_id: string;
  job_type: string;
  job_status: string;
  message: string;
}

export interface JobStatus {
  id: string;
  status: string;
  job_type: string;
  progress: number | null;
  progress_message: string | null;
  error_message: string | null;
  queued_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface Job {
  id: string;
  session_id: string | null;
  document_id: string | null;
  job_type: string;
  status: string;
  progress: number | null;
  progress_message: string | null;
  error_message: string | null;
  result_summary: string | null;
  queued_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface SessionStats {
  session_id: string;
  document_count: number;
  classified_document_count: number;
  income_item_count: number;
  deduction_item_count: number;
  needs_review_item_count: number;
  total_item_count: number;
}

export interface TaxItem {
  id: string;
  session_id: string;
  item_type: string;
  category: string;
  amount: number | null;
  description: string;
  confidence: number;
  needs_review: boolean;
  review_status: "draft" | "needs_review" | "confirmed" | "excluded" | "tax_agent_review";
  review_reason: string | null;
  ato_reference_hint: string | null;
  reviewed_at: string | null;
  reviewed_by: string | null;
  created_at: string;
}

export interface ClassificationResponse {
  item_id: string;
  document_id: string;
  session_id: string;
  item_type: string;
  category: string;
  amount: number | null;
  description: string;
  confidence: number;
  needs_review: boolean;
  review_reason: string | null;
  ato_reference_hint: string | null;
}

export interface ExportPackage {
  export_metadata: {
    generated_at: string;
    disclaimer: string;
    status: string;
  };
  session: {
    id: string;
    title: string;
    financial_year: string;
    status: string;
  };
  summary: {
    total_documents: number;
    total_items: number;
    income_count: number;
    deduction_count: number;
    needs_review_count: number;
    approved_count: number;
    total_income_aud: number;
    total_candidate_deductions_aud: number;
  };
  income_items: Array<{
    id: string;
    category: string;
    amount: number | null;
    description: string;
    confidence: number;
    status: string;
    review_reason: string | null;
  }>;
  deduction_items: Array<{
    id: string;
    category: string;
    amount: number | null;
    description: string;
    confidence: number;
    status: string;
    review_reason: string | null;
    ato_reference_hint: string | null;
  }>;
  needs_review_items: Array<{
    id: string;
    type: string;
    category: string;
    amount: number | null;
    description: string;
    review_reason: string | null;
  }>;
  out_of_scope_items: Array<{
    id: string;
    category: string;
    description: string;
  }>;
  source_documents: Array<{
    id: string;
    filename: string;
    mime_type: string;
    size_bytes: number | null;
    status: string;
  }>;
  export_warnings: string[];
}

export interface ExportRecord {
  id: string;
  session_id: string;
  format: string;
  item_count: number;
  total_amount: number | null;
  total_taxable: number | null;
  compliance_score: string | null;
  created_at: string;
}

export interface DocumentPage {
  id: string;
  document_id: string;
  page_number: number;
  text: string | null;
  confidence: number | null;
  ocr_method: string | null;
  created_at: string;
}

// ── Compliance ──────────────────────────────────────────────────────────────

export interface ComplianceSummary {
  documents_reviewed: number;
  income_items: number;
  deduction_items: number;
  out_of_scope_items: number;
  needs_review_items: number;
  evidence_complete: number;
  evidence_incomplete: number;
  fy_date_warnings: number;
  risk_counts: { low: number; medium: number; high: number };
}

export interface ComplianceItem {
  item_id: string;
  document_id: string | null;
  category: string;
  risk_level: "low" | "medium" | "high";
  review_status: string;
  evidence_status: string;
  date_in_financial_year: boolean;
  findings: string[];
  required_actions: string[];
  requires_tax_agent: boolean;
  tax_agent_reason: string | null;
}

export interface ComplianceResult {
  schema_version: string;
  tax_session_id: string;
  financial_year: string;
  generated_at: string;
  review_status: "completed" | "in_progress" | "blocked";
  export_readiness: {
    status: string;
    reason: string;
    fy_dates_validated: boolean;
  };
  summary: ComplianceSummary;
  items: ComplianceItem[];
  unresolved_questions: string[];
  tax_agent_review_triggers: string[];
}

export interface AuthSetupStatus {
  is_configured: boolean;
  auth_mode: "local";
  has_active_user: boolean;
}

export interface AuthSessionState {
  is_authenticated: boolean;
  app_state: "UNINITIALIZED" | "LOCKED" | "UNLOCKING" | "UNLOCKED" | "SESSION_EXPIRED";
  user_id?: string | null;
  display_name?: string | null;
  expires_at?: string | null;
}

export type AppAuthState = AuthSessionState["app_state"];

export interface AuthSetupResponse {
  recovery_key: string;
  app_state: "UNLOCKED";
  session_token?: string | null;
}

export interface Workspace {
  id: string;
  user_id: string;
  tax_year: string;
  label: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_opened_at: string | null;
}

export interface WorkspaceReviewSummary {
  total_items: number;
  draft: number;
  needs_review: number;
  confirmed: number;
  excluded: number;
  tax_agent_review: number;
  ready_for_export: boolean;
  blocking_reasons: string[];
}

export interface WorkspaceExportRecord {
  id: string;
  workspace_id: string | null;
  filename: string | null;
  status: string;
  format: string;
  encrypted: boolean;
  kdf: string | null;
  encryption_version: string | null;
  kdf_params_summary: string | null;
  created_at: string;
  downloaded_at: string | null;
  file_size: number | null;
  sha256: string | null;
  item_count: number;
  document_count: number | null;
  blocking_reasons: string | null;
}

export interface WorkspaceAuditEvent {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  changed_by: string | null;
  details: string | null;
  created_at: string;
}

// ── Request helpers ───────────────────────────────────────────────────────────

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${path} — ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

async function uploadFile(
  path: string,
  formData: FormData
): Promise<UploadResponse> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    body: formData,
    credentials: "include",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Upload error ${res.status}: ${path} — ${body}`);
  }
  return res.json() as Promise<UploadResponse>;
}

// ── Public API ───────────────────────────────────────────────────────────────

export const api = {
  /** GET /api/health */
  health: () => request<{ status: string }>("/api/health"),

  // ── Auth / Workspaces (Phase 3) ─────────────────────────────────────────
  authSetupStatus: () => request<AuthSetupStatus>("/api/auth/setup-status"),
  authSession: () => request<AuthSessionState>("/api/auth/session"),
  authSetup: (data: { master_password: string; display_name?: string; email?: string }) =>
    request<AuthSetupResponse>("/api/auth/setup", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  authUnlock: (data: { master_password: string }) =>
    request<AuthSessionState>("/api/auth/unlock", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  authLogout: () =>
    request<{ ok: boolean }>("/api/auth/logout", {
      method: "POST",
    }),
  listWorkspaces: () => request<Workspace[]>("/api/workspaces"),
  createWorkspace: (data: { tax_year: string; label: string }) =>
    request<Workspace>("/api/workspaces", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listWorkspaceItems: (workspaceId: string, reviewStatus?: string) =>
    request<TaxItem[]>(
      `/api/workspaces/${workspaceId}/items${reviewStatus ? `?review_status=${reviewStatus}` : ""}`
    ),
  setWorkspaceItemReviewStatus: (
    workspaceId: string,
    itemId: string,
    reviewStatus: "confirmed" | "needs_review" | "excluded" | "tax_agent_review",
    note?: string,
  ) =>
    request<TaxItem>(`/api/workspaces/${workspaceId}/items/${itemId}/review-status`, {
      method: "PATCH",
      body: JSON.stringify({ review_status: reviewStatus, note }),
    }),
  getWorkspaceReviewSummary: (workspaceId: string) =>
    request<WorkspaceReviewSummary>(`/api/workspaces/${workspaceId}/review-summary`),
  generateWorkspaceReviewPack: (
    workspaceId: string,
    data: { export_password: string; include_source_documents: boolean }
  ) =>
    request<WorkspaceExportRecord>(`/api/workspaces/${workspaceId}/review-pack/generate`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listWorkspaceReviewPacks: (workspaceId: string) =>
    request<WorkspaceExportRecord[]>(`/api/workspaces/${workspaceId}/review-pack`),
  workspaceReviewPackDownloadUrl: (workspaceId: string, exportId: string) =>
    `${BASE_URL}/api/workspaces/${workspaceId}/review-pack/${exportId}/download`,
  deleteWorkspaceReviewPack: (workspaceId: string, exportId: string) =>
    request<{ ok: boolean }>(`/api/workspaces/${workspaceId}/review-pack/${exportId}`, {
      method: "DELETE",
    }),
  listWorkspaceAuditEvents: (workspaceId: string, limit = 50, offset = 0) =>
    request<WorkspaceAuditEvent[]>(
      `/api/workspaces/${workspaceId}/audit-events?limit=${limit}&offset=${offset}`
    ),

  // ── Sessions ──────────────────────────────────────────────────────────────
  /** GET /api/sessions */
  listSessions: () => request<Session[]>("/api/sessions"),

  /** POST /api/sessions */
  createSession: (data: {
    title: string;
    financial_year: string;
    notes?: string;
  }) =>
    request<Session>("/api/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** GET /api/sessions/:id */
  getSession: (id: string) => request<Session>(`/api/sessions/${id}`),

  /** DELETE /api/sessions/:id — delete session and all its data */
  deleteSession: (sessionId: string) =>
    request<void>(`/api/sessions/${sessionId}`, { method: "DELETE" }),

  /** PATCH /api/sessions/:id — update session title, notes, status */
  updateSession: (
    sessionId: string,
    data: { title?: string; notes?: string; status?: string }
  ) =>
    request<Session>(`/api/sessions/${sessionId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  /** GET /api/sessions/:id/stats */
  getSessionStats: (id: string) => request<SessionStats>(`/api/sessions/${id}/stats`),

  // ── Documents ─────────────────────────────────────────────────────────────
  /** GET /api/documents?session_id=... */
  listDocuments: (sessionId: string) =>
    request<Document[]>(`/api/documents?session_id=${sessionId}`),

  /** POST /api/documents/upload (multipart) */
  uploadDocument: (
    sessionId: string,
    file: File,
    category: string,
    financialYear: string
  ) => {
    const fd = new FormData();
    fd.append("session_id", sessionId);
    fd.append("file", file);
    fd.append("category", category);
    fd.append("financial_year", financialYear);
    return uploadFile("/api/documents/upload", fd);
  },

  // ── Batch Upload ──────────────────────────────────────────────────
  /** POST /api/documents/upload/batch (multipart) */
  uploadDocumentsBatch: (
    sessionId: string,
    files: File[],
    category: string,
    financialYear: string
  ) => {
    const fd = new FormData();
    fd.append("session_id", sessionId);
    fd.append("category", category);
    fd.append("financial_year", financialYear);
    for (const f of files) {
      fd.append("files", f);
    }
    return uploadFile("/api/documents/upload/batch", fd);
  },

  // ── Items / Classification ────────────────────────────────────────────────
  /** GET /api/items?session_id=... */
  listItems: (sessionId: string, needsReview?: boolean) => {
    let path = `/api/items?session_id=${sessionId}`;
    if (needsReview !== undefined) path += `&needs_review=${needsReview}`;
    return request<TaxItem[]>(path);
  },

  /** POST /api/items/classify */
  classifyDocument: (data: {
    document_id: string;
    session_id: string;
    extracted_text: string;
    financial_year?: string;
    skill_context?: string;
  }) =>
    request<ClassificationResponse[]>("/api/items/classify", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** POST /api/items/:id/review */
  reviewItem: (itemId: string, needsReview: boolean, reason?: string) =>
    request<TaxItem>(`/api/items/${itemId}/review`, {
      method: "POST",
      body: JSON.stringify({ needs_review: needsReview, review_reason: reason }),
    }),

  // ── Bulk Review ───────────────────────────────────────────────────
  /** POST /api/items/bulk-review */
  bulkReviewItems: (itemIds: string[], needsReview: boolean, reason?: string) =>
    request<{ reviewed: number; needs_review: boolean }>("/api/items/bulk-review", {
      method: "POST",
      body: JSON.stringify({ item_ids: itemIds, needs_review: needsReview, review_reason: reason }),
    }),

  /** DELETE /api/items/:id */
  deleteItem: (itemId: string) =>
    request<void>(`/api/items/${itemId}`, { method: "DELETE" }),

  // ── Jobs ──────────────────────────────────────────────────────────────────
  /** GET /api/jobs?session_id=... */
  listJobs: (sessionId: string) =>
    request<Job[]>(`/api/jobs?session_id=${sessionId}`),

  /** GET /api/jobs/:id/status */
  getJobStatus: (jobId: string) =>
    request<JobStatus>(`/api/jobs/${jobId}/status`),

  // ── Export ────────────────────────────────────────────────────────────────
  /** GET /api/export/:sessionId — downloads JSON */
  exportSession: async (sessionId: string) => {
    const res = await fetch(`${BASE_URL}/api/export/${sessionId}`, {
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error(`Export error ${res.status}`);
    return res.json() as Promise<ExportPackage>;
  },

  /** GET /api/export/:sessionId/history */
  getExportHistory: (sessionId: string) =>
    request<ExportRecord[]>(`/api/export/${sessionId}/history`),

  /** GET /api/export/:sessionId?format=csv — opens CSV download in new tab */
  exportSessionCsv: (sessionId: string) => {
    window.open(`${BASE_URL}/api/export/${sessionId}?format=csv`, "_blank");
  },

  /** DELETE /api/documents/:id */
  deleteDocument: (documentId: string) =>
    request<void>(`/api/documents/${documentId}`, { method: "DELETE" }),

  /** PATCH /api/documents/:id */
  updateDocument: (documentId: string, data: { status?: string; category?: string }) =>
    request<Document>(`/api/documents/${documentId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  /** GET /api/documents/:id/pages */
  getDocumentPages: (documentId: string) =>
    request<DocumentPage[]>(`/api/documents/${documentId}/pages`),

  /** PATCH /api/items/:id — update item fields (e.g. amount) */
  updateItem: (itemId: string, data: Partial<{ amount: number | null; description: string; category: string }>) =>
    request<TaxItem>(`/api/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  // ── Compliance ─────────────────────────────────────────────────────
  /** GET /api/compliance/:sessionId */
  getCompliance: (sessionId: string) =>
    request<ComplianceResult>(`/api/compliance/${sessionId}`),
};
