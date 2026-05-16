"use client";

import { useEffect, useMemo, useState } from "react";
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
} from "@/lib/api";

type NavItem = "Dashboard" | "Documents" | "Review Items" | "Issues" | "Review Pack" | "Settings";
type StepStatus = "todo" | "in_progress" | "ready" | "blocked";
type ReviewFilter = "all" | "needs_review" | "confirmed" | "excluded" | "tax_agent_review";

const NAV_ITEMS: NavItem[] = ["Dashboard", "Documents", "Review Items", "Issues", "Review Pack", "Settings"];
const AUTH_EVENT_KEY = "taxai_auth_event";
const LOCK_MESSAGE = "Workspace is locked. Unlock to view sensitive tax data.";
const ALLOWED_UPLOAD_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".csv", ".txt"];
const ALLOWED_UPLOAD_MIME_TYPES = ["application/pdf", "image/png", "image/jpeg", "text/csv", "text/plain"];

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
  const [reviewFilter, setReviewFilter] = useState<ReviewFilter>("all");
  const [exportPassword, setExportPassword] = useState("");
  const [confirmExportPassword, setConfirmExportPassword] = useState("");
  const [exportHistory, setExportHistory] = useState<WorkspaceExportRecord[]>([]);
  const [auditEvents, setAuditEvents] = useState<WorkspaceAuditEvent[]>([]);
  const [securityStatus, setSecurityStatus] = useState<WorkspaceSecurityStatus | null>(null);
  const [recoveryCopied, setRecoveryCopied] = useState(false);
  const [resetSuccessMessage, setResetSuccessMessage] = useState<string | null>(null);

  const isAllowedUploadFile = (file: File): boolean => {
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    const type = (file.type || "").toLowerCase();
    return ALLOWED_UPLOAD_EXTENSIONS.includes(ext) || ALLOWED_UPLOAD_MIME_TYPES.includes(type);
  };

  const refreshReviewData = async (workspaceId: string, filter: ReviewFilter) => {
    try {
      const [summary, items] = await Promise.all([
        api.getWorkspaceReviewSummary(workspaceId),
        api.listWorkspaceItems(workspaceId, filter === "all" ? undefined : filter),
      ]);
      setReviewSummary(summary);
      setReviewItems(items);
      setMessage(null);
    } catch (err) {
      setReviewSummary(null);
      setReviewItems([]);
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

        setAuthState("UNLOCKED");
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
    if (!process.env.NEXT_PUBLIC_LOCK_ON_BROWSER_CLOSE || authState !== "UNLOCKED") return;
    const onBeforeUnload = () => {
      void api.authLogoutKeepalive();
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
  const manualReviewDocuments = documents.filter((d) => d.status === "needs_review").length;
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
              if (password.length < 8) {
                setMessage("Use at least 8 characters.");
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
            await api.authLogout();
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
                {documents.length} documents, {queuedOrRunningJobs} processing, {failedDocuments} failed, {duplicateDocuments} duplicates flagged, {manualReviewDocuments} manual review.
              </p>
              <p className="text-xs text-slate-500">Next step: add documents, then confirm items marked Needs Review.</p>
            </article>
            {reviewSummary && (
              <article className="rounded-lg border border-slate-200 bg-slate-50 p-3" data-testid="review-progress">
                <p className="text-xs text-slate-600">
                  Review progress: {reviewSummary.confirmed} confirmed, {reviewSummary.needs_review} needs review,{" "}
                  {reviewSummary.excluded} excluded, {reviewSummary.tax_agent_review} tax agent review.
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
                  type="file"
                  onChange={(e) => {
                    const file = e.target.files?.[0] ?? null;
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
                    try {
                      const uploadedFileName = uploadFile.name;
                      await api.uploadWorkspaceDocument(selectedWorkspaceId, uploadFile, "general", undefined, (percent) =>
                        setUploadProgress(percent)
                      );
                      const refreshedDocs = await refreshDocumentsAndJobs();
                      await refreshReviewData(selectedWorkspaceId, reviewFilter);
                      const duplicateDoc = refreshedDocs.find((d) => d.status === "duplicate_detected");
                      setUploadFile(null);
                      if (duplicateDoc) {
                        setMessage("Duplicate file detected. Review the document list and keep only the version you need.");
                      } else {
                        setMessage(`${uploadedFileName} uploaded. Processing has started.`);
                      }
                    } catch (err) {
                      if (isLockedResponseError(err)) {
                        setAuthState("LOCKED");
                        localStorage.setItem(AUTH_EVENT_KEY, "locked");
                        setMessage("Workspace is locked. Unlock to upload documents.");
                      } else if (err instanceof ApiError) {
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
              <p className="text-xs font-medium text-slate-700">Processing Queue</p>
              <p className="mt-1 text-xs text-slate-500">
                OCR and classification run in the background. Refresh status to see latest progress.
              </p>
              {jobsLoading && <p className="mt-2 text-xs text-slate-500">Loading processing status…</p>}
              {!jobsLoading && jobs.length === 0 && <p className="mt-2 text-xs text-slate-500">No processing jobs yet.</p>}
              <div className="mt-2 space-y-2">
                {jobs.slice(0, 8).map((job) => (
                  <div key={job.id} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs">
                    <p className="font-medium text-slate-700">{job.job_type.replaceAll("_", " ")}</p>
                    <p className="text-slate-500">Status: {job.status}</p>
                    {job.progress_message && <p className="text-slate-500">{job.progress_message}</p>}
                    {job.error_message && <p className="text-amber-700">{job.error_message}</p>}
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 p-3">
              <p className="text-xs font-medium text-slate-700">Workspace Documents</p>
              {documentsError && (
                <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-700">{documentsError}</p>
              )}
              {documentsLoading && <p className="mt-2 text-xs text-slate-500">Loading documents…</p>}
              <div className="mt-2 space-y-2">
                {documents.map((doc) => (
                  <article
                    key={doc.id}
                    className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700"
                    data-testid="document-row"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium">{doc.original_filename}</p>
                      <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-[11px] text-slate-600">
                        {toProcessingOutcome(doc.status).replaceAll("_", " ")}
                      </span>
                    </div>
                    <p className="mt-1 text-slate-500">{doc.created_at}</p>
                    <p className="mt-1 text-slate-500">
                      Items: {doc.item_count ?? 0} · Provider mode: {doc.provider_mode ?? "mock"}
                    </p>
                    {doc.status_reason && (
                      <p className="mt-1 text-slate-500">{doc.status_reason}</p>
                    )}
                    {doc.status === "duplicate_detected" && (
                      <p className="mt-1 text-amber-700">Duplicate detected. Keep or remove one copy during document cleanup.</p>
                    )}
                    {doc.status === "needs_review" && (
                      <p className="mt-1 text-amber-700">
                        Needs manual review. OCR/classification did not produce a complete item set for this document.
                      </p>
                    )}
                    {toProcessingOutcome(doc.status) === "failed" && (
                      <div className="mt-1">
                        <p className="text-amber-700">Processing could not complete for this file.</p>
                        {doc.retryable ? (
                          <button
                            type="button"
                            className="mt-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px]"
                            onClick={() => setMessage(`Try again: choose ${doc.original_filename} and upload once more.`)}
                          >
                            Try again
                          </button>
                        ) : (
                          <p className="mt-1 text-slate-500">This file needs manual review. Re-upload may not change the outcome.</p>
                        )}
                      </div>
                    )}
                  </article>
                ))}
                {!documentsLoading && documents.length === 0 && (
                  <p className="text-xs text-slate-500" data-testid="documents-empty-state">
                    No documents yet. Upload your first document to begin OCR and item extraction.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeNav === "Review Items" && (
          <div className="space-y-3" data-testid="review-items-panel">
            <article className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
              <p className="font-medium text-slate-700">Human Review Guidance</p>
              <p className="mt-1">Start with Needs Review, then Tax Agent Review, then confirm or exclude the remaining items.</p>
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
                  {reviewSummary.confirmed} confirmed · {reviewSummary.needs_review} need review · {reviewSummary.excluded} excluded · {reviewSummary.tax_agent_review} tax agent review
                </p>
              )}
              {reviewItems.map((item) => (
                <article key={item.id} className="rounded-lg border border-slate-200 p-3" data-testid="review-item-row">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm text-slate-700">{item.description || item.category}</p>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-600">
                      {item.review_status.replaceAll("_", " ")}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2" data-testid="item-status-actions">
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
                  <p>No items for this filter yet.</p>
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
                    exportPassword.length < 8 ||
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
                    <p className="text-slate-500">{e.created_at}</p>
                    <p className="text-slate-500">
                      {e.file_size ?? 0} bytes · sha256 {e.sha256 ? `${e.sha256.slice(0, 12)}...` : "n/a"} · {e.kdf ?? "kdf-n/a"}
                    </p>
                    {e.sha256 && (
                      <button
                        className="mt-1 rounded-md border border-slate-300 bg-white px-2 py-0.5 text-[11px]"
                        onClick={async () => {
                          await navigator.clipboard.writeText(e.sha256 ?? "");
                          setMessage("Checksum copied for local verification.");
                        }}
                      >
                        Copy checksum
                      </button>
                    )}
                    {e.downloaded_at && <p className="text-slate-500">Downloaded: {e.downloaded_at}</p>}
                  </div>
                  <div className="flex gap-2">
                    <a
                      className="rounded-md border border-slate-300 bg-white px-2 py-1"
                      href={selectedWorkspaceId ? api.workspaceReviewPackDownloadUrl(selectedWorkspaceId, e.id) : "#"}
                    >
                      Download
                    </a>
                    <button
                      className="rounded-md border border-slate-300 bg-white px-2 py-1"
                      onClick={async () => {
                        if (!selectedWorkspaceId) return;
                        await api.deleteWorkspaceReviewPack(selectedWorkspaceId, e.id);
                        const history = await api.listWorkspaceReviewPacks(selectedWorkspaceId);
                        setExportHistory(history);
                      }}
                    >
                      Delete
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
              await api.authLogout();
              setAuthState("LOCKED");
            }}
          >
            Lock workspace
          </button>
          <button
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs"
            onClick={() => setAuthState("SESSION_EXPIRED")}
          >
            Simulate session expiry
          </button>
        </div>
        <div className="mt-4">
          <h4 className="text-xs font-semibold text-slate-700">Recent Activity</h4>
          <div className="mt-2 space-y-2" data-testid="audit-events-panel">
            {auditEvents.slice(0, 8).map((event) => (
              <div key={event.id} className="rounded-md border border-slate-200 p-2 text-[11px] text-slate-600">
                <p className="font-medium text-slate-700">{event.action.replaceAll("_", " ")}</p>
                <p className="text-slate-500">{event.created_at}</p>
              </div>
            ))}
            {auditEvents.length === 0 && <p className="text-[11px] text-slate-500">No recent audit events.</p>}
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
