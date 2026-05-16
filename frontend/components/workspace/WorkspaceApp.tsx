"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import React from "react";
import {
  api,
  ApiError,
  type AppAuthState,
  type Document,
  type Job,
  type TaxItem,
  type Workspace,
  type WorkspaceExportRecord,
  type WorkspaceAuditEvent,
  type WorkspaceReviewSummary,
  type WorkspaceSecurityStatus,
  type ManualReviewDocument,
} from "@/lib/api";

type NavItem = "Dashboard" | "Documents" | "Review Items" | "Issues" | "Review Pack" | "Settings";
type StepStatus = "todo" | "in_progress" | "ready" | "blocked";
type ReviewFilter = "all" | "needs_review" | "confirmed" | "excluded" | "tax_agent_review";

const NAV_ITEMS: NavItem[] = ["Dashboard", "Documents", "Review Items", "Issues", "Review Pack", "Settings"];
const AUTH_EVENT_KEY = "taxai_auth_event";
const LOCK_MESSAGE = "Workspace is locked. Unlock to view sensitive tax data.";
const ALLOWED_UPLOAD_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".csv", ".txt"];
const ALLOWED_UPLOAD_MIME_TYPES = ["application/pdf", "image/png", "image/jpeg", "text/csv", "text/plain"];
const COMMON_WEAK_PASSWORDS = new Set([
  "password",
  "password123",
  "123456789012",
  "1234567890",
  "qwerty123",
  "letmein123",
  "admin123456",
  "welcome123",
  "changeme123",
]);

function isLockedResponseError(err: unknown): boolean {
  if (err instanceof ApiError) return err.status === 401 || err.status === 423;
  return err instanceof Error && (err.message.includes("API error 401") || err.message.includes("API error 423"));
}

function toProcessingOutcome(status: string): "uploaded" | "extracting" | "classifying" | "needs_review" | "classified" | "duplicate_detected" | "failed" {
  if (status === "uploaded" || status === "stored") return "uploaded";
  if (status === "extracting_text" || status === "text_extracted" || status === "ocr_required" || status === "ocr_completed") return "extracting";
  if (status === "classifying" || status === "ready_for_classification") return "classifying";
  if (status === "needs_review") return "needs_review";
  if (status === "classified" || status === "reviewed" || status === "included_in_report" || status === "exported") return "classified";
  if (status === "duplicate_detected") return "duplicate_detected";
  if (status === "classification_failed" || status === "extraction_failed" || status === "failed") return "failed";
  return "uploaded";
}

function outcomeLabel(status: string): string {
  const outcome = toProcessingOutcome(status);
  if (outcome === "duplicate_detected") return "Duplicate";
  if (outcome === "needs_review") return "Needs Review";
  if (outcome === "uploaded") return "Uploaded";
  if (outcome === "extracting") return "Extracting";
  if (outcome === "classifying") return "Classifying";
  if (outcome === "classified") return "Classified";
  if (outcome === "failed") return "Failed";
  return "Uploaded";
}

function formatDateTime(value?: string | null): string {
  if (!value) return "Unknown time";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "Unknown time";
  return dt.toLocaleString("en-AU", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function friendlyStatusReason(reason?: string | null): string | null {
  if (!reason) return null;
  const lower = reason.toLowerCase();
  if (lower.includes("provider_not_configured") || lower.includes("ai classification is not configured")) {
    return "AI classification is not configured correctly. Document needs manual review.";
  }
  if (lower.includes("classification_failed") || lower.includes("processing_failed")) {
    return "Processing failed. You can retry, replace, or delete this document.";
  }
  return reason;
}

function validateMasterPassword(password: string): string | null {
  const normalized = password.trim();
  if (normalized.length < 12) return "Use at least 12 characters.";
  if (/^\d+$/.test(normalized)) return "Password cannot be numbers only.";
  if (/^[A-Za-z]+$/.test(normalized)) return "Password cannot be letters only.";
  if (COMMON_WEAK_PASSWORDS.has(normalized.toLowerCase())) return "This password is too common. Choose a stronger password.";
  return null;
}

function inferItemNature(item: TaxItem): "income/earning" | "expense/cost" | "unknown" {
  const t = (item.item_type || "").toLowerCase();
  const c = (item.category || "").toLowerCase();
  if (t.includes("income") || c.includes("salary") || c.includes("wages")) return "income/earning";
  if (t.includes("deduction") || t.includes("expense") || c.includes("expense") || c.includes("cost") || c.includes("tools")) return "expense/cost";
  return "unknown";
}

type DuplicateUploadInfo = {
  existing_document: {
    id: string;
    original_filename: string;
    created_at: string;
    status: string;
  };
};

export function WorkspaceApp() {
  const [authState, setAuthState] = useState<AppAuthState>("UNLOCKING");
  const [setupStep, setSetupStep] = useState<"create" | "show_key" | "confirm_key">("create");
  const [password, setPassword] = useState("");
  const [unlockInput, setUnlockInput] = useState("");
  const [showRecoveryReset, setShowRecoveryReset] = useState(false);
  const [recoveryResetKey, setRecoveryResetKey] = useState("");
  const [recoveryResetPassword, setRecoveryResetPassword] = useState("");
  const [confirmInput, setConfirmInput] = useState("");
  const [recoveryKey, setRecoveryKey] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [activeNav, setActiveNav] = useState<NavItem>("Dashboard");

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>("");
  const [reviewSummary, setReviewSummary] = useState<WorkspaceReviewSummary | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isDragActive, setIsDragActive] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [reviewItems, setReviewItems] = useState<TaxItem[]>([]);
  const [manualReviewDocuments, setManualReviewDocuments] = useState<ManualReviewDocument[]>([]);
  const [reviewFilter, setReviewFilter] = useState<ReviewFilter>("all");
  const [exportPassword, setExportPassword] = useState("");
  const [confirmExportPassword, setConfirmExportPassword] = useState("");
  const [exportHistory, setExportHistory] = useState<WorkspaceExportRecord[]>([]);
  const [downloadingExportId, setDownloadingExportId] = useState<string | null>(null);
  const [deletingExportId, setDeletingExportId] = useState<string | null>(null);
  const [auditEvents, setAuditEvents] = useState<WorkspaceAuditEvent[]>([]);
  const [securityStatus, setSecurityStatus] = useState<WorkspaceSecurityStatus | null>(null);
  const [recoveryCopied, setRecoveryCopied] = useState(false);
  const [resetSuccessMessage, setResetSuccessMessage] = useState<string | null>(null);
  const [queueCollapsed, setQueueCollapsed] = useState(true);
  const [documentsCollapsed, setDocumentsCollapsed] = useState(false);
  const [showAllJobs, setShowAllJobs] = useState(false);
  const [showAllDocuments, setShowAllDocuments] = useState(false);
  const [activityCollapsed, setActivityCollapsed] = useState(true);
  const [showAllActivity, setShowAllActivity] = useState(false);
  const [highlightDocumentId, setHighlightDocumentId] = useState<string | null>(null);
  const [pendingScrollDocumentId, setPendingScrollDocumentId] = useState<string | null>(null);
  const [idleTimeoutMinutes, setIdleTimeoutMinutes] = useState<number>(() => {
    if (typeof window === "undefined") return 15;
    return Number(window.localStorage.getItem("taxai_idle_timeout_minutes") || 15);
  });
  const [selectedItem, setSelectedItem] = useState<TaxItem | null>(null);
  const [duplicateUploadInfo, setDuplicateUploadInfo] = useState<DuplicateUploadInfo | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const documentRowRefs = useRef<Record<string, HTMLElement | null>>({});

  const isAllowedUploadFile = (file: File): boolean => {
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    const type = (file.type || "").toLowerCase();
    return ALLOWED_UPLOAD_EXTENSIONS.includes(ext) || ALLOWED_UPLOAD_MIME_TYPES.includes(type);
  };

  const showToast = (text: string) => {
    setToast(text);
    window.setTimeout(() => setToast(null), 2800);
  };

  const computeFileHash = async (file: File): Promise<string | null> => {
    try {
      const buffer = await file.arrayBuffer();
      const digest = await crypto.subtle.digest("SHA-256", buffer);
      return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
    } catch {
      return null;
    }
  };

  const refreshReviewData = async (workspaceId: string, filter: ReviewFilter) => {
    try {
      const [summary, items, manualDocs] = await Promise.all([
        api.getWorkspaceReviewSummary(workspaceId),
        api.listWorkspaceItems(workspaceId, filter === "all" ? undefined : filter),
        api.listWorkspaceManualReviewDocuments(workspaceId),
      ]);
      setReviewSummary(summary);
      setReviewItems(items);
      setManualReviewDocuments(manualDocs);
      setMessage(null);
    } catch (err) {
      setReviewSummary(null);
      setReviewItems([]);
      setManualReviewDocuments([]);
      if (isLockedResponseError(err)) {
        setAuthState("LOCKED");
        localStorage.setItem(AUTH_EVENT_KEY, "locked");
      }
      setMessage(LOCK_MESSAGE);
      throw err;
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        const setup = await api.authSetupStatus();
        if (!setup.is_configured) {
          setAuthState("UNINITIALIZED");
          return;
        }

        const session = await api.authSession();
        if (!session.is_authenticated) {
          setAuthState(session.app_state === "SESSION_EXPIRED" ? "SESSION_EXPIRED" : "LOCKED");
          return;
        }
        setAuthState(session.app_state === "UNLOCKED" ? "UNLOCKED" : "LOCKED");
      } catch {
        setAuthState("LOCKED");
      }
    };
    void init();
  }, []);

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key !== AUTH_EVENT_KEY || !event.newValue) return;
      if (event.newValue === "locked") setAuthState("LOCKED");
      if (event.newValue === "expired") setAuthState("SESSION_EXPIRED");
      if (event.newValue === "unlocked") setAuthState("UNLOCKED");
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  useEffect(() => {
    if (authState !== "UNLOCKED") return;
    const interval = window.setInterval(async () => {
      try {
        const session = await api.authSession();
        if (!session.is_authenticated) {
          const next = session.app_state === "SESSION_EXPIRED" ? "SESSION_EXPIRED" : "LOCKED";
          setAuthState(next);
          localStorage.setItem(AUTH_EVENT_KEY, next === "SESSION_EXPIRED" ? "expired" : "locked");
        }
      } catch {
        setAuthState("LOCKED");
        localStorage.setItem(AUTH_EVENT_KEY, "locked");
      }
    }, 60000);
    return () => window.clearInterval(interval);
  }, [authState]);

  useEffect(() => {
    if (authState !== "UNLOCKED") return;
    const onBeforeUnload = () => {
      void api.authLockKeepalive();
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [authState]);

  useEffect(() => {
    if (authState !== "UNLOCKED") return;
    void (async () => {
      try {
        const list = await api.listWorkspaces();
        setWorkspaces(list);
        if (list.length > 0) setSelectedWorkspaceId(list[0].id);
      } catch {
        setMessage("Unable to load workspaces.");
        if (authState === "UNLOCKED") {
          setAuthState("LOCKED");
          localStorage.setItem(AUTH_EVENT_KEY, "locked");
        }
      }
    })();
  }, [authState]);

  useEffect(() => {
    if (authState !== "UNLOCKED" || !selectedWorkspaceId) return;
    void (async () => {
      try {
        await refreshReviewData(selectedWorkspaceId, reviewFilter);
      } catch {
        // handled in refreshReviewData
      }
    })();
  }, [authState, selectedWorkspaceId, reviewFilter]);

  useEffect(() => {
    if (authState !== "UNLOCKED" || !selectedWorkspaceId || activeNav !== "Documents") return;
    void (async () => {
      setDocumentsLoading(true);
      setDocumentsError(null);
      try {
        const docs = await api.listWorkspaceDocuments(selectedWorkspaceId);
        setDocuments(docs);
        if (docs.length > 0) {
          setJobsLoading(true);
          try {
            const jobList = await api.listJobs(docs[0].session_id);
            setJobs(jobList);
          } catch {
            setJobs([]);
          } finally {
            setJobsLoading(false);
          }
        } else {
          setJobs([]);
        }
      } catch (err) {
        if (isLockedResponseError(err)) {
          setAuthState("LOCKED");
          localStorage.setItem(AUTH_EVENT_KEY, "locked");
        }
        setDocuments([]);
        setJobs([]);
        setDocumentsError("Unable to load documents for this workspace.");
        setMessage("Unable to load documents for this workspace.");
      } finally {
        setDocumentsLoading(false);
      }
    })();
  }, [authState, selectedWorkspaceId, activeNav]);

  useEffect(() => {
    if (!pendingScrollDocumentId || activeNav !== "Documents") return;
    const el = documentRowRefs.current[pendingScrollDocumentId];
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    setHighlightDocumentId(pendingScrollDocumentId);
    setPendingScrollDocumentId(null);
    const timer = window.setTimeout(() => setHighlightDocumentId(null), 2200);
    return () => window.clearTimeout(timer);
  }, [pendingScrollDocumentId, activeNav, documents]);

  useEffect(() => {
    if (authState !== "UNLOCKED" || !selectedWorkspaceId) return;
    void (async () => {
      try {
        const docs = await api.listWorkspaceDocuments(selectedWorkspaceId);
        setDocuments(docs);
        if (docs.length > 0) {
          const jobList = await api.listJobs(docs[0].session_id);
          setJobs(jobList);
        } else {
          setJobs([]);
        }
      } catch {
        // Keep current view stable; detailed errors are handled in Documents panel.
      }
    })();
  }, [authState, selectedWorkspaceId]);

  useEffect(() => {
    setToast(null);
  }, [activeNav]);

  useEffect(() => {
    if (authState !== "UNLOCKED" || !selectedWorkspaceId) return;
    void (async () => {
      try {
        const status = await api.getWorkspaceSecurityStatus(selectedWorkspaceId);
        setSecurityStatus(status);
      } catch {
        setSecurityStatus(null);
      }
    })();
  }, [authState, selectedWorkspaceId]);

  useEffect(() => {
    if (authState !== "UNLOCKED" || !selectedWorkspaceId) return;
    void (async () => {
      try {
        const events = await api.listWorkspaceAuditEvents(selectedWorkspaceId, 20, 0);
        setAuditEvents(events);
      } catch {
        setAuditEvents([]);
      }
    })();
  }, [authState, selectedWorkspaceId]);

  useEffect(() => {
    if (authState !== "UNLOCKED" || !selectedWorkspaceId) return;
    void (async () => {
      try {
        const history = await api.listWorkspaceReviewPacks(selectedWorkspaceId);
        setExportHistory(history);
      } catch {
        setExportHistory([]);
      }
    })();
  }, [authState, selectedWorkspaceId]);

  const selectedWorkspace = workspaces.find((w) => w.id === selectedWorkspaceId) ?? workspaces[0];
  const navigateToNav = (target: NavItem) => {
    if (typeof window !== "undefined") {
      console.debug("[WorkspaceApp] nav-click", {
        from_url: window.location.href,
        target_nav: target,
        selected_workspace_id: selectedWorkspace?.id ?? null,
      });
    }
    if (!selectedWorkspace?.id) {
      setMessage("No workspace selected. Choose a Tax Year Workspace to continue.");
      return;
    }
    setActiveNav(target);
    setMessage(null);
  };

  const stepState = useMemo<{
    documents: StepStatus;
    review: StepStatus;
    issues: StepStatus;
    pack: StepStatus;
  }>(() => {
    return {
      documents: selectedWorkspace ? "ready" : "todo",
      review: selectedWorkspace ? (reviewSummary?.needs_review ? "in_progress" : "ready") : "blocked",
      issues: selectedWorkspace ? (reviewSummary?.tax_agent_review ? "in_progress" : "todo") : "blocked",
      pack: selectedWorkspace ? (reviewSummary?.ready_for_export ? "ready" : "blocked") : "blocked",
    };
  }, [selectedWorkspace, reviewSummary]);

  const refreshDocumentsAndJobs = async (): Promise<Document[]> => {
    if (!selectedWorkspaceId) return [];
    setDocumentsLoading(true);
    setDocumentsError(null);
    try {
      const docs = await api.listWorkspaceDocuments(selectedWorkspaceId);
      setDocuments(docs);
      if (docs.length > 0) {
        setJobsLoading(true);
        try {
          const jobList = await api.listJobs(docs[0].session_id);
          setJobs(jobList);
        } catch {
          setJobs([]);
        } finally {
          setJobsLoading(false);
        }
      } else {
        setJobs([]);
      }
      return docs;
    } catch {
      setDocuments([]);
      setJobs([]);
      setDocumentsError("Unable to refresh documents.");
      return [];
    } finally {
      setDocumentsLoading(false);
    }
  };

  const queuedOrRunningJobs = jobs.filter((j) => j.status === "queued" || j.status === "running" || j.status === "retrying").length;
  const failedJobs = jobs.filter((j) => j.status === "failed").length;
  const duplicateDocuments = documents.filter((d) => d.status === "duplicate_detected").length;
  const failedDocuments = documents.filter((d) => d.status === "classification_failed" || d.status === "extraction_failed").length;
  const manualReviewDocumentCount = documents.filter((d) => d.status === "needs_review").length;
  const hasAnyDocuments = documents.length > 0;
  const hasMockOrManualProvider = documents.some((d) => d.provider_mode === "mock" || d.provider_mode === "manual");

  const setItemStatus = async (
    itemId: string,
    status: "confirmed" | "needs_review" | "excluded" | "tax_agent_review"
  ) => {
    if (!selectedWorkspaceId) return;
    try {
      await api.setWorkspaceItemReviewStatus(selectedWorkspaceId, itemId, status);
      await refreshReviewData(selectedWorkspaceId, reviewFilter);
      setMessage(null);
    } catch (err) {
      if (isLockedResponseError(err)) {
        setAuthState("LOCKED");
        localStorage.setItem(AUTH_EVENT_KEY, "locked");
      }
      setMessage(LOCK_MESSAGE);
    }
  };

  if (authState === "UNLOCKING") {
    return <AuthCard title="Loading" subtitle="Checking workspace lock state..." />;
  }

  if (authState === "UNINITIALIZED") {
    return (
      <AuthCard title="Create Master Password" subtitle="Set up your local workspace lock.">
        {setupStep === "create" && (
          <form
            className="space-y-3"
            onSubmit={async (e) => {
              e.preventDefault();
              const pwdError = validateMasterPassword(password);
              if (pwdError) {
                setMessage(pwdError);
                return;
              }
              try {
                const res = await api.authSetup({ master_password: password });
                setRecoveryKey(res.recovery_key);
                setSetupStep("show_key");
                setMessage(null);
              } catch (err) {
                setMessage(err instanceof Error ? err.message : "Setup failed");
              }
            }}
          >
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Master password"
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
            />
            {message && <p className="text-xs text-amber-700">{message}</p>}
            <button className="rounded-md border border-slate-300 bg-slate-900 px-4 py-2 text-sm text-white">Continue</button>
          </form>
        )}

        {setupStep === "show_key" && (
          <div className="space-y-3">
            <p className="text-sm text-slate-600">Recovery Key (show once):</p>
            <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-sm text-slate-800">{recoveryKey}</div>
            <p className="text-xs text-amber-700">
              Store this key offline. Losing both master password and recovery key permanently loses encrypted data access.
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm"
                onClick={async () => {
                  await navigator.clipboard.writeText(recoveryKey);
                  setRecoveryCopied(true);
                  showToast("Recovery key copied.");
                }}
              >
                Copy Key
              </button>
              <button
                type="button"
                className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm"
                onClick={() => {
                  const blob = new Blob([`Tax Return AI Recovery Key\n${recoveryKey}\n`], { type: "text/plain;charset=utf-8" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = "tax-return-ai-recovery-key.txt";
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                Download Key
              </button>
            </div>
            {recoveryCopied && <p className="text-xs text-slate-500">Recovery key copied.</p>}
            <button className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm" onClick={() => setSetupStep("confirm_key")}>
              I saved it
            </button>
          </div>
        )}

        {setupStep === "confirm_key" && (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (confirmInput.trim() !== recoveryKey.trim()) {
                setMessage("Recovery key does not match.");
                return;
              }
              setMessage(null);
              setAuthState("UNLOCKED");
            }}
          >
            <p className="text-sm text-slate-600">Confirm recovery key to finish setup.</p>
            <input
              value={confirmInput}
              onChange={(e) => setConfirmInput(e.target.value.toUpperCase())}
              placeholder="XXXXXX-XXXXXX-XXXXXX-XXXXXX"
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
            />
            {message && <p className="text-xs text-amber-700">{message}</p>}
            <button className="rounded-md border border-slate-300 bg-slate-900 px-4 py-2 text-sm text-white">Finish setup</button>
          </form>
        )}
      </AuthCard>
    );
  }

  if (authState === "LOCKED") {
    return (
      <AuthCard title="Unlock Workspace" subtitle="Enter master password to continue.">
        {!showRecoveryReset ? (
          <form
            className="space-y-3"
            onSubmit={async (e) => {
              e.preventDefault();
              setAuthState("UNLOCKING");
              try {
                const session = await api.authUnlock({ master_password: unlockInput });
                if (session.is_authenticated || session.app_state === "UNLOCKED") {
                  setMessage(null);
                  setAuthState("UNLOCKED");
                  localStorage.setItem(AUTH_EVENT_KEY, "unlocked");
                } else {
                  setAuthState("LOCKED");
                  setMessage("Invalid password.");
                }
              } catch {
                setAuthState("LOCKED");
                setMessage("Invalid password.");
              }
            }}
          >
            <input
              type="password"
              value={unlockInput}
              onChange={(e) => setUnlockInput(e.target.value)}
              placeholder="Master password"
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
            />
            {message && <p className="text-xs text-amber-700">{message}</p>}
            <button className="rounded-md border border-slate-300 bg-slate-900 px-4 py-2 text-sm text-white">Unlock</button>
            <button type="button" className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm" onClick={() => setShowRecoveryReset(true)}>
              Forgot Password
            </button>
          </form>
        ) : (
          <form
            className="space-y-3"
            onSubmit={async (e) => {
              e.preventDefault();
              const pwdError = validateMasterPassword(recoveryResetPassword);
              if (pwdError) {
                setMessage(pwdError);
                return;
              }
              try {
                const session = await api.authRecoverReset({
                  recovery_key: recoveryResetKey,
                  new_master_password: recoveryResetPassword,
                });
                if (session.is_authenticated || session.app_state === "UNLOCKED") {
                  setMessage(null);
                  setResetSuccessMessage("Password reset complete. Keep your recovery key safe for future resets.");
                  setAuthState("UNLOCKED");
                  localStorage.setItem(AUTH_EVENT_KEY, "unlocked");
                }
              } catch {
                setMessage("Recovery reset failed. Check recovery key.");
              }
            }}
          >
            <p className="text-xs text-amber-700">
              Recovery key restores encrypted data access. Losing both password and recovery key permanently loses data.
            </p>
            <input
              value={recoveryResetKey}
              onChange={(e) => setRecoveryResetKey(e.target.value.toUpperCase())}
              placeholder="Recovery key"
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
            />
            <input
              type="password"
              value={recoveryResetPassword}
              onChange={(e) => setRecoveryResetPassword(e.target.value)}
              placeholder="New master password"
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
            />
            {message && <p className="text-xs text-amber-700">{message}</p>}
            <button className="rounded-md border border-slate-300 bg-slate-900 px-4 py-2 text-sm text-white">Reset Password</button>
            <button type="button" className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm" onClick={() => setShowRecoveryReset(false)}>
              Back
            </button>
          </form>
        )}
      </AuthCard>
    );
  }

  if (authState === "SESSION_EXPIRED") {
    return (
      <AuthCard title="Session Expired" subtitle="Your workspace was locked due to inactivity.">
        <button className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm" onClick={() => setAuthState("LOCKED")}>
          Return to unlock
        </button>
      </AuthCard>
    );
  }

  return (
    <div className="grid min-h-[78vh] grid-cols-12 gap-4" data-testid="unlocked-shell">
      <aside className="col-span-12 rounded-xl border border-slate-200 bg-white p-4 md:col-span-3">
        <h1 className="text-base font-semibold text-slate-900">Tax Return AI</h1>
        <p className="mt-1 text-xs text-slate-500">Local-first tax evidence review</p>
        <nav className="mt-4 space-y-1" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <button
              key={item}
              onClick={() => setActiveNav(item)}
              className={`w-full rounded-md px-3 py-2 text-left text-sm ${
                activeNav === item ? "bg-slate-100 text-slate-900" : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              {item}
            </button>
          ))}
        </nav>
        <button
          className="mt-4 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
          onClick={async () => {
            await api.authLock();
            setAuthState("LOCKED");
            localStorage.setItem(AUTH_EVENT_KEY, "locked");
          }}
        >
          Lock Workspace
        </button>
      </aside>

      <section className="col-span-12 rounded-xl border border-slate-200 bg-white p-5 md:col-span-6">
        <header className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">{activeNav}</h2>
            <p className="text-xs text-slate-500">Documents are stored locally; database encryption is planned next. Encrypted review packs are enabled. Cloud AI remains optional.</p>
          </div>
          <div className="flex items-center gap-2" data-testid="tax-year-selector">
            <label htmlFor="tax-year" className="text-xs text-slate-500">
              Tax Year Workspace
            </label>
            <select
              id="tax-year"
              value={selectedWorkspace?.id ?? ""}
              onChange={(e) => setSelectedWorkspaceId(e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs"
            >
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.tax_year}
                </option>
              ))}
            </select>
          </div>
        </header>
        {message && (
          <div className="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            {message}
          </div>
        )}
        {toast && (
          <div className="mb-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800" data-testid="toast-notification">
            {toast}
          </div>
        )}
        {duplicateUploadInfo && (
          <div className="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800" data-testid="duplicate-upload-info">
            <p className="font-medium">This document was already uploaded.</p>
            <p className="mt-1">
              Existing: {duplicateUploadInfo.existing_document.original_filename} · {formatDateTime(duplicateUploadInfo.existing_document.created_at)} · {outcomeLabel(duplicateUploadInfo.existing_document.status)}
            </p>
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                className="rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px] text-slate-700"
                onClick={() => {
                  setActiveNav("Documents");
                  setUploadFile(null);
                  setUploadProgress(0);
                  setMessage(null);
                  if (fileInputRef.current) fileInputRef.current.value = "";
                  setDocumentsCollapsed(false);
                  setPendingScrollDocumentId(duplicateUploadInfo.existing_document.id);
                  setDuplicateUploadInfo(null);
                }}
              >
                View existing document
              </button>
              <button
                type="button"
                className="rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px] text-slate-700"
                onClick={() => {
                  setDuplicateUploadInfo(null);
                  setUploadFile(null);
                  setUploadProgress(0);
                  if (fileInputRef.current) fileInputRef.current.value = "";
                }}
              >
                Cancel upload
              </button>
            </div>
          </div>
        )}
        {resetSuccessMessage && (
          <div className="mb-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
            {resetSuccessMessage}
          </div>
        )}

        {activeNav === "Dashboard" && (
          <div className="space-y-3" data-testid="guided-steps">
            <article className="rounded-lg border border-slate-200 bg-slate-50 p-3" data-testid="workspace-health-summary">
              <p className="text-xs font-medium text-slate-700">Workspace Health</p>
              <p className="mt-1 text-xs text-slate-600">
                {documents.length} documents, {queuedOrRunningJobs} processing, {failedDocuments} failed, {duplicateDocuments} duplicates flagged, {manualReviewDocumentCount} manual review.
              </p>
              <p className="text-xs text-slate-500">Next step: add documents, then confirm items marked Needs Review.</p>
            </article>
            {reviewSummary && (
              <article className="rounded-lg border border-slate-200 bg-slate-50 p-3" data-testid="review-progress">
                <p className="text-xs text-slate-600">
                  Review progress: {reviewSummary.confirmed} confirmed, {reviewSummary.needs_review} needs review,{" "}
                  {reviewSummary.excluded} excluded, {reviewSummary.tax_agent_review} tax agent review,{" "}
                  {reviewSummary.manual_review_documents ?? 0} document blockers.
                </p>
              </article>
            )}
            <GuidedStep
              title="Step 1: Add documents"
              status={stepState.documents}
              description="Upload payslips, statements, and receipts for this tax year."
              action={<NavActionButton onClick={() => navigateToNav("Documents")}>Open Documents</NavActionButton>}
            />
            <GuidedStep
              title="Step 2: Review extracted items"
              status={stepState.review}
              description="Confirm inferred income and deduction items before they are included in the review pack."
              action={<NavActionButton onClick={() => navigateToNav("Review Items")}>Open Review Items</NavActionButton>}
            />
            <GuidedStep
              title="Step 3: Resolve issues"
              status={stepState.issues}
              description="Resolve items marked Needs Review, Excluded, or Tax Agent Review."
              action={<NavActionButton onClick={() => navigateToNav("Issues")}>Open Issues</NavActionButton>}
            />
            <GuidedStep
              title="Step 4: Generate review pack"
              status={stepState.pack}
              description="Export the current workspace for human review and handoff."
              action={<NavActionButton onClick={() => navigateToNav("Review Pack")}>Open Review Pack</NavActionButton>}
              disabled={!reviewSummary?.ready_for_export}
            />
          </div>
        )}

        {activeNav === "Documents" && (
          <div className="space-y-3" data-testid="documents-panel">
            <div className="rounded-lg border border-slate-200 p-3">
              <p className="text-xs font-medium text-slate-700">Upload Document</p>
              <p className="mt-1 text-xs text-slate-500">
                Add payslips, statements, or receipts to this workspace.
              </p>
              <div
                className={`mt-3 rounded-md border border-dashed p-3 ${isDragActive ? "border-slate-500 bg-slate-50" : "border-slate-300 bg-white"}`}
                data-testid="documents-dropzone"
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragActive(true);
                }}
                onDragLeave={() => setIsDragActive(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragActive(false);
                  const file = e.dataTransfer.files?.[0];
                  if (!file) return;
                  setDuplicateUploadInfo(null);
                  if (!isAllowedUploadFile(file)) {
                    setMessage("Unsupported file type. Allowed formats: PDF, PNG, JPG/JPEG, CSV, TXT.");
                    return;
                  }
                  setUploadFile(file);
                }}
              >
                <p className="text-xs text-slate-500">Drag and drop a file here, or choose one below.</p>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <input
                  data-testid="documents-file-input"
                  ref={fileInputRef}
                  type="file"
                  onChange={(e) => {
                    const file = e.target.files?.[0] ?? null;
                    setDuplicateUploadInfo(null);
                    if (!file) {
                      setUploadFile(null);
                      return;
                    }
                    if (!isAllowedUploadFile(file)) {
                      setUploadFile(null);
                      setMessage("Unsupported file type. Allowed formats: PDF, PNG, JPG/JPEG, CSV, TXT.");
                      return;
                    }
                    setUploadFile(file);
                  }}
                  className="text-xs text-slate-600 file:rounded-md file:border file:border-slate-300 file:bg-white file:px-2 file:py-1 file:text-xs"
                />
                <button
                  type="button"
                  className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700"
                  onClick={() => void refreshDocumentsAndJobs()}
                >
                  Refresh status
                </button>
                <button
                  type="button"
                  className="rounded-md border border-slate-300 bg-slate-900 px-3 py-1.5 text-xs text-white disabled:opacity-50"
                  disabled={!selectedWorkspaceId || !uploadFile || uploadingDocument}
                  onClick={async () => {
                    if (!selectedWorkspaceId || !uploadFile) return;
                    if (!isAllowedUploadFile(uploadFile)) {
                      setMessage("Unsupported file type. Allowed formats: PDF, PNG, JPG/JPEG, CSV, TXT.");
                      return;
                    }
                    setUploadingDocument(true);
                    setUploadProgress(0);
                    setDuplicateUploadInfo(null);
                    try {
                      const uploadedFileName = uploadFile.name;
                      const selectedHash = await computeFileHash(uploadFile);
                      let sameFilenameWarningShown = false;
                      const hasSameFilename = documents.some(
                        (d) => d.original_filename.toLowerCase() === uploadedFileName.toLowerCase()
                      );
                      if (hasSameFilename) {
                        if (!selectedHash) {
                          showToast("A document with this filename already exists.");
                          sameFilenameWarningShown = true;
                        } else {
                          const sameNameDifferentContent = documents.some(
                            (d) =>
                              d.original_filename.toLowerCase() === uploadedFileName.toLowerCase() &&
                              d.file_hash &&
                              d.file_hash !== selectedHash
                          );
                          if (sameNameDifferentContent) {
                            showToast("A document with this filename already exists.");
                            sameFilenameWarningShown = true;
                          }
                        }
                      }
                      await api.uploadWorkspaceDocument(selectedWorkspaceId, uploadFile, "general", undefined, (percent) =>
                        setUploadProgress(percent)
                      );
                      const refreshedDocs = await refreshDocumentsAndJobs();
                      await refreshReviewData(selectedWorkspaceId, reviewFilter);
                      const duplicateDoc = refreshedDocs.find((d) => d.status === "duplicate_detected");
                      setUploadFile(null);
                      if (duplicateDoc) {
                        showToast("Duplicate file detected. Review and remove the duplicate copy if needed.");
                      } else if (!sameFilenameWarningShown) {
                        showToast(`${uploadedFileName} uploaded. Processing has started.`);
                      }
                    } catch (err) {
                      if (isLockedResponseError(err)) {
                        setAuthState("LOCKED");
                        localStorage.setItem(AUTH_EVENT_KEY, "locked");
                        setMessage("Workspace is locked. Unlock to upload documents.");
                      } else if (err instanceof ApiError) {
                        if (err.code === "duplicate_file" && err.detail && typeof err.detail === "object") {
                          const existing = (err.detail as { existing_document?: DuplicateUploadInfo["existing_document"] }).existing_document;
                          if (existing) {
                            setDuplicateUploadInfo({ existing_document: existing });
                          }
                          showToast("This document was already uploaded.");
                        } else
                        if (err.code === "unsupported_file_type" || err.status === 415) {
                          setMessage("Unsupported file type. Allowed formats: PDF, PNG, JPG/JPEG, CSV, TXT.");
                        } else if (err.code === "file_too_large") {
                          setMessage(err.message);
                        } else if (err.retryable || err.code === "temporary_processing_failure") {
                          setMessage("Temporary processing failure. Try again.");
                        } else {
                          setMessage(err.message || "Upload failed.");
                        }
                      } else {
                        setMessage("Upload failed. Please try again.");
                      }
                    } finally {
                      setUploadingDocument(false);
                      setUploadProgress(0);
                    }
                  }}
                >
                  {uploadingDocument ? "Uploading..." : "Upload document"}
                </button>
              </div>
              {uploadFile && <p className="mt-2 text-xs text-slate-500">Selected file: {uploadFile.name}</p>}
              {uploadingDocument && (
                <div className="mt-2" data-testid="upload-progress">
                  <div className="h-2 w-full rounded bg-slate-100">
                    <div className="h-2 rounded bg-slate-500 transition-all" style={{ width: `${uploadProgress}%` }} />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">Upload progress: {uploadProgress}%</p>
                </div>
              )}
            </div>
            <div className="rounded-lg border border-slate-200 p-3" data-testid="processing-queue-panel">
              <button
                type="button"
                className="flex w-full items-center justify-between gap-2 text-left"
                onClick={() => setQueueCollapsed((v) => !v)}
              >
                <p className="text-xs font-medium text-slate-700">Processing Queue</p>
                <span className={`text-xs text-slate-500 transition-transform ${queueCollapsed ? "" : "rotate-180"}`}>⌄</span>
              </button>
              <div className={`overflow-hidden transition-all duration-200 ${queueCollapsed ? "max-h-0" : "max-h-[900px]"}`}>
                <p className="mt-1 text-xs text-slate-500">
                  OCR and classification run in the background. Refresh status to see latest progress.
                </p>
                {!jobsLoading && jobs.length === 0 && <p className="mt-2 text-xs text-slate-500">No processing jobs yet.</p>}
                {jobsLoading && <p className="mt-2 text-xs text-slate-500">Loading processing status…</p>}
                <div className="mt-2 space-y-2">
                  {(showAllJobs ? jobs : jobs.slice(0, 4)).map((job) => (
                    <div key={job.id} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs">
                      <p className="font-medium text-slate-700">{job.job_type.replaceAll("_", " ")}</p>
                      <p className="text-slate-500">
                        Status: <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-[11px] text-slate-700">{job.status}</span>
                      </p>
                      {job.progress_message && <p className="text-slate-500">{job.progress_message}</p>}
                      {job.error_message && <p className="text-amber-700">{job.error_message}</p>}
                    </div>
                  ))}
                  {jobs.length > 4 && (
                    <button
                      type="button"
                      className="rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px]"
                      onClick={() => setShowAllJobs((v) => !v)}
                    >
                      {showAllJobs ? "Show less" : `Show more (${jobs.length - 4})`}
                    </button>
                  )}
                </div>
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 p-3">
              <button
                type="button"
                className="flex w-full items-center justify-between gap-2 text-left"
                onClick={() => setDocumentsCollapsed((v) => !v)}
              >
                <p className="text-xs font-medium text-slate-700">Workspace Documents</p>
                <span className={`text-xs text-slate-500 transition-transform ${documentsCollapsed ? "" : "rotate-180"}`}>⌄</span>
              </button>
              <div className={`overflow-hidden transition-all duration-200 ${documentsCollapsed ? "max-h-0" : "max-h-[1200px]"}`}>
              {documentsLoading && <p className="mt-2 text-xs text-slate-500">Loading documents…</p>}
              {!documentsLoading && (
              <div className="mt-2 space-y-2">
                {(showAllDocuments ? documents : documents.slice(0, 5)).map((doc) => (
                  <article
                    key={doc.id}
                    ref={(el) => {
                      documentRowRefs.current[doc.id] = el;
                    }}
                    className={`rounded-md border px-3 py-2 text-xs text-slate-700 transition-colors ${
                      highlightDocumentId === doc.id ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-slate-50"
                    }`}
                    data-testid="document-row"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium">{doc.original_filename}</p>
                      <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-[11px] text-slate-600">
                        {outcomeLabel(doc.status)}
                      </span>
                    </div>
                    <p className="mt-1 text-slate-500">{formatDateTime(doc.created_at)}</p>
                    <p className="mt-1 text-slate-500">
                      Items: {doc.item_count ?? 0} · Provider mode: {doc.provider_mode ?? "manual"}
                    </p>
                    <p className="mt-1 text-slate-500">
                      OCR: {doc.extraction_status ?? "pending"} ({doc.extraction_text_length ?? 0} chars) · Classification: {doc.classification_status ?? "pending"}
                      {doc.classification_provider ? ` via ${doc.classification_provider}` : ""}
                    </p>
                    {friendlyStatusReason(doc.status_reason) && (
                      <p className="mt-1 text-slate-500">{friendlyStatusReason(doc.status_reason)}</p>
                    )}
                    {doc.status === "duplicate_detected" && (
                      <div className="mt-1">
                        <p className="text-amber-700">Duplicate detected. The original document is kept.</p>
                        <div className="mt-1 flex gap-2">
                          <span className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-[11px] text-amber-800">Duplicate</span>
                          <button
                            type="button"
                            className="rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px]"
                            onClick={async () => {
                              const confirmed = window.confirm(`Remove duplicate document "${doc.original_filename}"? The original document will be kept.`);
                              if (!confirmed) return;
                              await api.deleteWorkspaceDocument(doc.id);
                              await refreshDocumentsAndJobs();
                              showToast("Duplicate document removed.");
                            }}
                          >
                            Review duplicate
                          </button>
                        </div>
                      </div>
                    )}
                    {doc.status === "needs_review" && (
                      <p className="mt-1 text-amber-700">
                        Needs manual review. OCR/classification did not produce a complete item set for this document.
                      </p>
                    )}
                    {toProcessingOutcome(doc.status) === "failed" && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px]"
                          onClick={() => {
                            setMessage(`Retry: choose ${doc.original_filename} and upload again.`);
                            fileInputRef.current?.focus();
                          }}
                        >
                          Retry processing
                        </button>
                        <button
                          type="button"
                          className="rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px]"
                          onClick={() => {
                            setMessage(`Replace document: choose ${doc.original_filename} and upload again.`);
                            fileInputRef.current?.focus();
                          }}
                        >
                          Replace document
                        </button>
                        <button
                          type="button"
                          className="rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px]"
                          onClick={async () => {
                            const confirmed = window.confirm(`Delete failed document "${doc.original_filename}"?`);
                            if (!confirmed) return;
                            await api.deleteWorkspaceDocument(doc.id);
                            await refreshDocumentsAndJobs();
                            showToast("Failed document deleted.");
                          }}
                        >
                          Delete failed document
                        </button>
                      </div>
                    )}
                  </article>
                ))}
                {documents.length > 5 && (
                  <button
                    type="button"
                    className="rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px]"
                    onClick={() => setShowAllDocuments((v) => !v)}
                  >
                    {showAllDocuments ? "Show less" : `Show more (${documents.length - 5})`}
                  </button>
                )}
                {!documentsLoading && documents.length === 0 && (
                  <p className="text-xs text-slate-500" data-testid="documents-empty-state">
                    No documents yet. Upload your first document to begin.
                  </p>
                )}
              </div>
              )}
              </div>
              {documentsError && (
                <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-700">{documentsError}</p>
              )}
            </div>
          </div>
        )}

        {activeNav === "Review Items" && (
          <div className="space-y-3" data-testid="review-items-panel">
            <article className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
              <p className="font-medium text-slate-700">Human Review Guidance</p>
              <p className="mt-1">Start with Needs Review, then Tax Agent Review, then confirm or exclude the remaining items.</p>
              <ul className="mt-2 list-disc pl-5">
                <li>Confirmed = user reviewed and accepts this item for review pack.</li>
                <li>Needs Review = user still needs to check details.</li>
                <li>Excluded = do not include in review pack.</li>
                <li>Tax Agent Review = include as a question for professional review.</li>
              </ul>
            </article>
            <div className="flex flex-wrap gap-2" data-testid="review-filters">
              {[
                { key: "all", label: "All" },
                { key: "needs_review", label: "Needs Review" },
                { key: "confirmed", label: "Confirmed" },
                { key: "excluded", label: "Excluded" },
                { key: "tax_agent_review", label: "Tax Agent Review" },
              ].map((f) => (
                <button
                  key={f.key}
                  className={`rounded-md border px-2 py-1 text-xs ${reviewFilter === f.key ? "border-slate-500 bg-slate-100" : "border-slate-300 bg-white"}`}
                  onClick={() => setReviewFilter(f.key as ReviewFilter)}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <div className="space-y-2">
              {reviewSummary && (
                <p className="text-xs text-slate-500">
                  {reviewSummary.confirmed} confirmed · {reviewSummary.needs_review} need review · {reviewSummary.excluded} excluded · {reviewSummary.tax_agent_review} tax agent review · {reviewSummary.manual_review_documents ?? 0} document blockers
                </p>
              )}
              {manualReviewDocuments.length > 0 && (
                <div className="space-y-2" data-testid="manual-review-documents">
                  <p className="text-xs font-medium text-slate-700">Documents needing manual review</p>
                  {manualReviewDocuments.map((doc) => (
                    <article key={doc.id} className="rounded-lg border border-amber-200 bg-amber-50 p-3" data-testid="manual-review-document-card">
                      <p className="text-sm font-medium text-slate-800">{doc.filename}</p>
                      <p className="mt-1 text-xs text-slate-600">
                        Outcome: {outcomeLabel(doc.status)} · Provider: {doc.provider_mode} · Status: {friendlyStatusReason(doc.status_reason) ?? "Needs manual review"}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <StatusActionButton
                          onClick={async () => {
                            if (!selectedWorkspaceId) return;
                            await api.createWorkspaceManualItem(selectedWorkspaceId, doc.id, {
                              description: `Manual review item for ${doc.filename}`,
                              review_status: "needs_review",
                              item_type: "needs_review",
                              category: "needs_review",
                            });
                            await refreshReviewData(selectedWorkspaceId, reviewFilter);
                            await refreshDocumentsAndJobs();
                            showToast("Manual review item added.");
                          }}
                        >
                          Add manual item
                        </StatusActionButton>
                        <StatusActionButton
                          onClick={async () => {
                            if (!selectedWorkspaceId) return;
                            await api.applyWorkspaceManualReviewAction(selectedWorkspaceId, doc.id, "exclude_document");
                            await refreshReviewData(selectedWorkspaceId, reviewFilter);
                            await refreshDocumentsAndJobs();
                            showToast("Document excluded from review pack.");
                          }}
                        >
                          Mark document excluded
                        </StatusActionButton>
                        <StatusActionButton
                          onClick={async () => {
                            if (!selectedWorkspaceId) return;
                            await api.applyWorkspaceManualReviewAction(selectedWorkspaceId, doc.id, "tax_agent_review");
                            await api.createWorkspaceManualItem(selectedWorkspaceId, doc.id, {
                              description: `Tax agent review needed for ${doc.filename}`,
                              review_status: "tax_agent_review",
                              item_type: "needs_review",
                              category: "needs_review",
                            });
                            await refreshReviewData(selectedWorkspaceId, reviewFilter);
                            await refreshDocumentsAndJobs();
                            showToast("Sent to Tax Agent Review.");
                          }}
                        >
                          Send to Tax Agent Review
                        </StatusActionButton>
                        <StatusActionButton
                          onClick={() => {
                            setActiveNav("Documents");
                            setDocumentsCollapsed(false);
                            setPendingScrollDocumentId(doc.id);
                          }}
                        >
                          View document
                        </StatusActionButton>
                      </div>
                    </article>
                  ))}
                </div>
              )}
              {reviewItems.map((item) => (
                <article key={item.id} className="rounded-lg border border-slate-200 p-3" data-testid="review-item-row">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <p className="text-sm text-slate-700">{item.description || item.category}</p>
                      <p className="text-[11px] text-slate-500">Type: {inferItemNature(item)}</p>
                    </div>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-600">
                      {item.review_status.replaceAll("_", " ")}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2" data-testid="item-status-actions">
                    <StatusActionButton onClick={() => setSelectedItem(item)}>View details</StatusActionButton>
                    {item.review_status !== "confirmed" && (
                      <StatusActionButton onClick={() => void setItemStatus(item.id, "confirmed")}>Confirm</StatusActionButton>
                    )}
                    {item.review_status !== "needs_review" && (
                      <StatusActionButton onClick={() => void setItemStatus(item.id, "needs_review")}>Needs Review</StatusActionButton>
                    )}
                    {item.review_status !== "excluded" && (
                      <StatusActionButton onClick={() => void setItemStatus(item.id, "excluded")}>Exclude</StatusActionButton>
                    )}
                    {item.review_status !== "tax_agent_review" && (
                      <StatusActionButton onClick={() => void setItemStatus(item.id, "tax_agent_review")}>Tax Agent Review</StatusActionButton>
                    )}
                  </div>
                </article>
              ))}
              {reviewItems.length === 0 && (
                <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
                  <p>No extracted items yet. Review the documents below or add a manual item.</p>
                  {(reviewSummary?.total_items ?? 0) === 0 && hasAnyDocuments && (
                    <p className="mt-1">Documents exist but no items were extracted yet. Open Documents to review processing outcomes.</p>
                  )}
                  {(reviewSummary?.total_items ?? 0) === 0 && !hasAnyDocuments && (
                    <p className="mt-1">Upload a document first, then return to review extracted items.</p>
                  )}
                  {hasMockOrManualProvider && (
                    <p className="mt-1">Manual review mode is active for this workspace. You can still continue by reviewing document outcomes.</p>
                  )}
                  <button
                    type="button"
                    className="mt-2 rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px]"
                    onClick={() => setActiveNav("Documents")}
                  >
                    Go to Documents
                  </button>
                </div>
              )}
            </div>
            {selectedItem && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/35 p-4">
                <div className="w-full max-w-xl rounded-lg border border-slate-200 bg-white p-4 text-xs text-slate-700">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold">Review Item Details</h4>
                    <button className="rounded border border-slate-300 px-2 py-1" onClick={() => setSelectedItem(null)}>Close</button>
                  </div>
                  <div className="mt-3 space-y-1">
                    <p><span className="font-medium">Provider/Seller:</span> Not extracted yet</p>
                    <p><span className="font-medium">Description:</span> {selectedItem.description || "Not extracted yet"}</p>
                    <p><span className="font-medium">Amount:</span> {selectedItem.amount ?? "Not extracted yet"}</p>
                    <p><span className="font-medium">Category:</span> {selectedItem.category || "Not extracted yet"}</p>
                    <p><span className="font-medium">Inferred type:</span> {inferItemNature(selectedItem)}</p>
                    <p><span className="font-medium">Source document:</span> {documents.find((d) => d.session_id === selectedItem.session_id)?.original_filename ?? "Not extracted yet"}</p>
                    <p><span className="font-medium">Confidence:</span> {selectedItem.confidence ?? "Not extracted yet"}</p>
                    <p><span className="font-medium">Evidence snippets:</span> Not extracted yet</p>
                    <p><span className="font-medium">Reviewer notes:</span> {selectedItem.review_reason || "Not extracted yet"}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeNav === "Issues" && (
          <div className="space-y-2 text-sm text-slate-600" data-testid="issues-placeholder">
            {(reviewSummary?.tax_agent_review ?? 0) > 0 ? (
              <>
                <p>Items marked Tax Agent Review need attention.</p>
                <p>Current tax agent review count: {reviewSummary?.tax_agent_review ?? 0}</p>
                <p>Issue engine is not fully configured yet, so this list is a guided placeholder.</p>
              </>
            ) : (
              <>
                <p>No issues found in the current review status.</p>
                <p>Issue engine is not configured yet; advanced checks will appear here in a later phase.</p>
              </>
            )}
          </div>
        )}

        {activeNav === "Review Pack" && (
          <div className="space-y-2 text-sm text-slate-600" data-testid="review-pack-panel">
            <p>Encrypted review pack is {reviewSummary?.ready_for_export ? "ready" : "not ready"}.</p>
            <p className="text-xs text-slate-500">
              This package is prepared for human review, not a final tax return, and not submitted to ATO.
            </p>
            <p className="text-xs text-slate-500">Verify downloaded file checksum against the SHA-256 listed below.</p>
            <article className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs" data-testid="review-pack-summary">
              <p className="font-medium text-slate-700">Current workspace summary</p>
              <p className="mt-1 text-slate-600">
                Confirmed items: {reviewSummary?.confirmed ?? 0} · Excluded items: {reviewSummary?.excluded ?? 0} · Tax Agent Review items: {reviewSummary?.tax_agent_review ?? 0}
              </p>
              <p className="text-slate-600">
                Documents referenced: {documents.filter((d) => (d.item_count ?? 0) > 0).length} of {documents.length}
              </p>
            </article>
            {!reviewSummary?.ready_for_export &&
              (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs" data-testid="review-pack-blockers">
                  <p className="font-medium text-amber-900">Export is blocked</p>
                  {reviewSummary?.blocking_reasons?.length ? (
                    <ul className="mt-1 list-disc pl-5 text-amber-800">
                      {reviewSummary.blocking_reasons.map((r) => (
                        <li key={r}>{r}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-amber-800">Export is disabled until review items are confirmed or excluded.</p>
                  )}
                  <p className="mt-2 text-amber-900">Next step: resolve review items, then re-check this page.</p>
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      className="rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px] text-slate-700"
                      onClick={() => setActiveNav("Review Items")}
                    >
                      Go to Review Items
                    </button>
                    <button
                      type="button"
                      className="rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px] text-slate-700"
                      onClick={() => setActiveNav("Documents")}
                    >
                      Go to Documents
                    </button>
                  </div>
                </div>
              )}
            {reviewSummary?.ready_for_export && (
              <div className="mt-3 space-y-2 rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-700">Generate Encrypted Review Pack</p>
                <ul className="list-disc pl-5 text-xs text-slate-600">
                  <li>Review summary prepared for human review</li>
                  <li>Extracted item list for cross-checking</li>
                  <li>Evidence reference index for supporting documents</li>
                </ul>
                <p className="text-xs text-amber-700">
                  This password is required to open the encrypted review pack. It cannot be recovered.
                </p>
                <p className="text-xs text-slate-500">Minimum length: 12 characters.</p>
                <input
                  type="password"
                  value={exportPassword}
                  onChange={(e) => setExportPassword(e.target.value)}
                  placeholder="Export password"
                  className="w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-xs"
                />
                <input
                  type="password"
                  value={confirmExportPassword}
                  onChange={(e) => setConfirmExportPassword(e.target.value)}
                  placeholder="Confirm export password"
                  className="w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-xs"
                />
                {confirmExportPassword.length > 0 && exportPassword !== confirmExportPassword && (
                  <p className="text-xs text-rose-700">Passwords do not match.</p>
                )}
                {exportPassword.length > 0 && (
                  <p className="text-xs text-slate-500">
                    Strength hint: {exportPassword.length >= 16 ? "strong length" : exportPassword.length >= 12 ? "acceptable length" : "too short"}
                  </p>
                )}
                <button
                  className="rounded-md border border-slate-300 bg-slate-900 px-3 py-1 text-xs text-white disabled:opacity-50"
                  disabled={
                    !selectedWorkspaceId ||
                    exportPassword.length < 12 ||
                    exportPassword !== confirmExportPassword
                  }
                  onClick={async () => {
                    if (!selectedWorkspaceId) return;
                    await api.generateWorkspaceReviewPack(selectedWorkspaceId, {
                      export_password: exportPassword,
                      include_source_documents: false,
                    });
                    const [history, summary] = await Promise.all([
                      api.listWorkspaceReviewPacks(selectedWorkspaceId),
                      api.getWorkspaceReviewSummary(selectedWorkspaceId),
                    ]);
                    setExportHistory(history);
                    setReviewSummary(summary);
                    setExportPassword("");
                    setConfirmExportPassword("");
                  }}
                >
                  Generate Encrypted Review Pack
                </button>
              </div>
            )}
            <div className="mt-3 space-y-2" data-testid="export-history">
              <p className="text-xs text-slate-700">Export History</p>
              {exportHistory.map((e) => (
                <div key={e.id} className="flex items-center justify-between rounded-md border border-slate-200 p-2 text-xs">
                  <div>
                    <p>{e.filename ?? e.id}</p>
                    <p className="text-slate-500">{formatDateTime(e.created_at)}</p>
                    <p className="text-slate-500">
                      {e.file_size ?? 0} bytes · sha256 {e.sha256 ? `${e.sha256.slice(0, 12)}...` : "n/a"} · {e.kdf ?? "kdf-n/a"}
                    </p>
                    {e.sha256 && (
                      <button
                        className="mt-1 rounded-md border border-slate-300 bg-white px-2 py-0.5 text-[11px]"
                        onClick={async () => {
                          await navigator.clipboard.writeText(e.sha256 ?? "");
                          showToast("Checksum copied for local verification.");
                        }}
                      >
                        Copy checksum
                      </button>
                    )}
                    {e.downloaded_at && <p className="text-slate-500">Downloaded: {formatDateTime(e.downloaded_at)}</p>}
                  </div>
                  <div className="flex gap-2">
                    <button
                      className="rounded-md border border-slate-300 bg-white px-2 py-1 disabled:opacity-50"
                      disabled={!selectedWorkspaceId || downloadingExportId === e.id}
                      type="button"
                      onClick={async () => {
                        if (!selectedWorkspaceId) return;
                        setDownloadingExportId(e.id);
                        try {
                          const { blob, filename } = await api.downloadWorkspaceReviewPack(selectedWorkspaceId, e.id);
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = filename;
                          document.body.appendChild(a);
                          a.click();
                          a.remove();
                          URL.revokeObjectURL(url);
                          showToast("Encrypted review pack downloaded.");
                        } catch (err) {
                          if (err instanceof ApiError && err.status === 404) {
                            showToast("Review pack is no longer available. Generate a new one.");
                            const history = await api.listWorkspaceReviewPacks(selectedWorkspaceId);
                            setExportHistory(history);
                          } else if (isLockedResponseError(err)) {
                            setAuthState("LOCKED");
                            localStorage.setItem(AUTH_EVENT_KEY, "locked");
                            setMessage("Workspace is locked. Unlock to download review packs.");
                          } else {
                            showToast("Download failed. Try again.");
                          }
                        } finally {
                          setDownloadingExportId(null);
                        }
                      }}
                    >
                      {downloadingExportId === e.id ? "Downloading..." : "Download"}
                    </button>
                    <button
                      className="rounded-md border border-slate-300 bg-white px-2 py-1 disabled:opacity-50"
                      disabled={!selectedWorkspaceId || deletingExportId === e.id}
                      type="button"
                      onClick={async () => {
                        if (!selectedWorkspaceId) return;
                        setDeletingExportId(e.id);
                        try {
                          await api.deleteWorkspaceReviewPack(selectedWorkspaceId, e.id);
                          setExportHistory((prev) => prev.filter((row) => row.id !== e.id));
                          showToast("Review pack deleted.");
                          const history = await api.listWorkspaceReviewPacks(selectedWorkspaceId);
                          setExportHistory(history);
                        } catch (err) {
                          if (err instanceof ApiError && err.status === 404) {
                            setExportHistory((prev) => prev.filter((row) => row.id !== e.id));
                            showToast("Review pack was already removed.");
                          } else if (isLockedResponseError(err)) {
                            setAuthState("LOCKED");
                            localStorage.setItem(AUTH_EVENT_KEY, "locked");
                            setMessage("Workspace is locked. Unlock to manage review packs.");
                          } else {
                            showToast("Could not delete review pack. Try again.");
                          }
                        } finally {
                          setDeletingExportId(null);
                        }
                      }}
                    >
                      {deletingExportId === e.id ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                </div>
              ))}
              {exportHistory.length === 0 && <p className="text-xs text-slate-500">No exports yet.</p>}
            </div>
          </div>
        )}

        {activeNav === "Settings" && (
          <div className="space-y-3" data-testid="security-settings-panel">
            <h3 className="text-sm font-semibold text-slate-800">Security Status</h3>
            <article className="rounded-lg border border-slate-200 p-3 text-xs text-slate-600">
              <p className="font-semibold text-slate-700">Session idle timeout</p>
              <p className="mt-1">Choose how long the workspace stays unlocked when inactive.</p>
              <div className="mt-2 flex items-center gap-2">
                <select
                  value={idleTimeoutMinutes}
                  onChange={(e) => setIdleTimeoutMinutes(Number(e.target.value))}
                  className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs"
                >
                  <option value={5}>5 minutes</option>
                  <option value={15}>15 minutes</option>
                  <option value={30}>30 minutes</option>
                  <option value={60}>60 minutes</option>
                </select>
                <button
                  type="button"
                  className="rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px]"
                  onClick={() => {
                    localStorage.setItem("taxai_idle_timeout_minutes", String(idleTimeoutMinutes));
                    showToast("Session timeout preference saved.");
                  }}
                >
                  Save
                </button>
              </div>
            </article>
            {!securityStatus && <p className="text-xs text-slate-500">Security status unavailable.</p>}
            {securityStatus && (
              <>
                <article className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                  <p>Field encryption: {securityStatus.encryption_enabled}</p>
                  <p>Export encryption: {securityStatus.export_encryption_enabled ? "enabled" : "disabled"}</p>
                  <p>Session state: {securityStatus.session_status}</p>
                  <p>Recovery key configured: {securityStatus.recovery_key_configured ? "yes" : "no"}</p>
                  <p>Last unlock activity: {securityStatus.last_unlock_at ?? "n/a"}</p>
                </article>
                <article className="rounded-lg border border-slate-200 p-3 text-xs text-slate-600">
                  <p className="font-semibold text-slate-700">Plaintext Migration Progress</p>
                  <p>Overall completion: {securityStatus.plaintext_readiness.overall_migration_completion_percent}%</p>
                  <p>Document pages: {securityStatus.plaintext_readiness.document_pages.migration_completion_percent}%</p>
                  <p>Tax items: {securityStatus.plaintext_readiness.tax_items.migration_completion_percent}%</p>
                  <p>Classification results: {securityStatus.plaintext_readiness.classification_results.migration_completion_percent}%</p>
                  <p>
                    Plaintext fallback retirement:{" "}
                    {securityStatus.migration_readiness.can_disable_plaintext_fallback ? "ready" : "blocked"}
                  </p>
                </article>
                <article className="rounded-lg border border-slate-200 p-3 text-xs text-slate-600">
                  <p className="font-semibold text-slate-700">Operational Visibility</p>
                  <p>Backup status: {securityStatus.operational_visibility.backup_status}</p>
                  <p>Locked write counter: {securityStatus.operational_visibility.locked_write_counter}</p>
                  <p>Failed unlock counter: {securityStatus.operational_visibility.failed_unlock_counter}</p>
                </article>
              </>
            )}
          </div>
        )}

      </section>

      <aside className="col-span-12 rounded-xl border border-slate-200 bg-white p-4 md:col-span-3">
        <h3 className="text-sm font-semibold text-slate-800">Privacy</h3>
        <div className="mt-3 space-y-2 rounded-lg border border-slate-100 bg-slate-50 p-3 text-xs text-slate-600">
          <p>Your documents stay local by default.</p>
          <p>Cloud AI is off unless explicitly enabled.</p>
          <p>Encrypted review pack exports are enabled.</p>
        </div>
        <div className="mt-4 space-y-2">
          <button
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs"
            onClick={async () => {
              await api.authLock();
              setAuthState("LOCKED");
            }}
          >
            Lock workspace
          </button>
          {process.env.NEXT_PUBLIC_ENABLE_DEV_SESSION_SIMULATOR === "true" && (
            <button
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs"
              onClick={() => setAuthState("SESSION_EXPIRED")}
            >
              Simulate session expiry
            </button>
          )}
        </div>
        <div className="mt-4">
          <button
            type="button"
            className="flex w-full items-center justify-between"
            onClick={() => setActivityCollapsed((v) => !v)}
          >
            <h4 className="text-xs font-semibold text-slate-700">Recent Activity</h4>
            <span className={`text-xs text-slate-500 transition-transform ${activityCollapsed ? "" : "rotate-180"}`}>⌄</span>
          </button>
          <div className={`overflow-hidden transition-all duration-200 ${activityCollapsed ? "max-h-0" : "max-h-[900px]"}`}>
          <div className="mt-2 space-y-2" data-testid="audit-events-panel">
            {(showAllActivity ? auditEvents : auditEvents.slice(0, 5)).map((event) => (
              <div key={event.id} className="rounded-md border border-slate-200 p-2 text-[11px] text-slate-600">
                <p className="font-medium text-slate-700">{event.action.replaceAll("_", " ")}</p>
                <p className="text-slate-500">{formatDateTime(event.created_at)}</p>
              </div>
            ))}
            {auditEvents.length > 5 && (
              <button
                type="button"
                className="rounded-md border border-slate-300 bg-white px-2 py-0.5 text-[11px]"
                onClick={() => setShowAllActivity((v) => !v)}
              >
                {showAllActivity ? "Show less" : `Show more (${auditEvents.length - 5})`}
              </button>
            )}
            {auditEvents.length === 0 && <p className="text-[11px] text-slate-500">No recent audit events.</p>}
          </div>
          </div>
        </div>
      </aside>
    </div>
  );
}

function AuthCard({ title, subtitle, children }: { title: string; subtitle: string; children?: React.ReactNode }) {
  return (
    <div className="mx-auto mt-10 max-w-md rounded-xl border border-slate-200 bg-white p-6" data-testid={title.toLowerCase().replace(/\s+/g, "-")}>
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
      <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
      {children && <div className="mt-5">{children}</div>}
    </div>
  );
}

function GuidedStep({
  title,
  description,
  status,
  action,
  disabled = false,
}: {
  title: string;
  description: string;
  status: StepStatus;
  action: React.ReactNode;
  disabled?: boolean;
}) {
  const badge = {
    todo: "Needs setup",
    in_progress: "Needs Review",
    ready: "Confirmed",
    blocked: "Blocked",
  }[status];

  return (
    <article className="rounded-lg border border-slate-200 p-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-medium text-slate-800">{title}</h3>
        <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-600">{badge}</span>
      </div>
      <p className="mt-1 text-xs text-slate-500">{description}</p>
      <div className={`mt-2 ${status === "blocked" || disabled ? "opacity-45 pointer-events-none" : ""}`}>{action}</div>
    </article>
  );
}

function NavActionButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
    >
      {children}
    </button>
  );
}

function StatusActionButton({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button onClick={onClick} className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700">
      {children}
    </button>
  );
}
