"use client";

import { useEffect, useMemo, useState } from "react";
import React from "react";
import Link from "next/link";
import { api, type AppAuthState, type TaxItem, type Workspace, type WorkspaceReviewSummary } from "@/lib/api";

type NavItem = "Dashboard" | "Documents" | "Review Items" | "Issues" | "Review Pack" | "Settings";
type StepStatus = "todo" | "in_progress" | "ready" | "blocked";
type ReviewFilter = "all" | "needs_review" | "confirmed" | "excluded" | "tax_agent_review";

const NAV_ITEMS: NavItem[] = ["Dashboard", "Documents", "Review Items", "Issues", "Review Pack", "Settings"];

export function WorkspaceApp() {
  const [authState, setAuthState] = useState<AppAuthState>("UNLOCKING");
  const [setupStep, setSetupStep] = useState<"create" | "show_key" | "confirm_key">("create");
  const [password, setPassword] = useState("");
  const [unlockInput, setUnlockInput] = useState("");
  const [confirmInput, setConfirmInput] = useState("");
  const [recoveryKey, setRecoveryKey] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [activeNav, setActiveNav] = useState<NavItem>("Dashboard");

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>("");
  const [reviewSummary, setReviewSummary] = useState<WorkspaceReviewSummary | null>(null);
  const [reviewItems, setReviewItems] = useState<TaxItem[]>([]);
  const [reviewFilter, setReviewFilter] = useState<ReviewFilter>("all");

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
    if (authState !== "UNLOCKED") return;
    void (async () => {
      try {
        const list = await api.listWorkspaces();
        setWorkspaces(list);
        if (list.length > 0) setSelectedWorkspaceId(list[0].id);
      } catch {
        setMessage("Unable to load workspaces.");
      }
    })();
  }, [authState]);

  useEffect(() => {
    if (authState !== "UNLOCKED" || !selectedWorkspaceId) return;
    void (async () => {
      try {
        const summary = await api.getWorkspaceReviewSummary(selectedWorkspaceId);
        setReviewSummary(summary);
      } catch {
        setReviewSummary(null);
      }
    })();
  }, [authState, selectedWorkspaceId]);

  useEffect(() => {
    if (authState !== "UNLOCKED" || !selectedWorkspaceId) return;
    void (async () => {
      try {
        const items = await api.listWorkspaceItems(
          selectedWorkspaceId,
          reviewFilter === "all" ? undefined : reviewFilter
        );
        setReviewItems(items);
      } catch {
        setReviewItems([]);
      }
    })();
  }, [authState, selectedWorkspaceId, reviewFilter]);

  const selectedWorkspace = workspaces.find((w) => w.id === selectedWorkspaceId) ?? workspaces[0];
  const selectedWorkspaceRouteId = selectedWorkspace?.id ?? "";
  const workspacePath = (section: "documents" | "items" | "issues" | "review-pack") =>
    selectedWorkspaceRouteId ? `/${section}?workspace_id=${selectedWorkspaceRouteId}` : `/${section}`;

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

  const setItemStatus = async (
    itemId: string,
    status: "confirmed" | "needs_review" | "excluded" | "tax_agent_review"
  ) => {
    if (!selectedWorkspaceId) return;
    await api.setWorkspaceItemReviewStatus(selectedWorkspaceId, itemId, status);
    const [summary, items] = await Promise.all([
      api.getWorkspaceReviewSummary(selectedWorkspaceId),
      api.listWorkspaceItems(selectedWorkspaceId, reviewFilter === "all" ? undefined : reviewFilter),
    ]);
    setReviewSummary(summary);
    setReviewItems(items);
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
        </form>
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
      </aside>

      <section className="col-span-12 rounded-xl border border-slate-200 bg-white p-5 md:col-span-6">
        <header className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">{activeNav}</h2>
            <p className="text-xs text-slate-500">Workspace lock is enabled. Document encryption is planned next.</p>
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

        {activeNav === "Dashboard" && (
          <div className="space-y-3" data-testid="guided-steps">
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
              action={<LinkButton href={workspacePath("documents")}>Open Documents</LinkButton>}
            />
            <GuidedStep
              title="Step 2: Review extracted items"
              status={stepState.review}
              description="Confirm inferred income and deduction items before they are included in the review pack."
              action={<LinkButton href={workspacePath("items")}>Open Review Items</LinkButton>}
            />
            <GuidedStep
              title="Step 3: Resolve issues"
              status={stepState.issues}
              description="Resolve items marked Needs Review, Excluded, or Tax Agent Review."
              action={<LinkButton href={workspacePath("issues")}>Open Issues</LinkButton>}
            />
            <GuidedStep
              title="Step 4: Generate review pack"
              status={stepState.pack}
              description="Export the current workspace for human review and handoff."
              action={<LinkButton href={workspacePath("review-pack")}>Open Review Pack</LinkButton>}
              disabled={!reviewSummary?.ready_for_export}
            />
          </div>
        )}

        {activeNav === "Review Items" && (
          <div className="space-y-3" data-testid="review-items-panel">
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
              {reviewItems.map((item) => (
                <article key={item.id} className="rounded-lg border border-slate-200 p-3" data-testid="review-item-row">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm text-slate-700">{item.description || item.category}</p>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-600">
                      {item.review_status.replaceAll("_", " ")}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2" data-testid="item-status-actions">
                    <StatusActionButton onClick={() => void setItemStatus(item.id, "confirmed")}>Confirm</StatusActionButton>
                    <StatusActionButton onClick={() => void setItemStatus(item.id, "needs_review")}>Needs Review</StatusActionButton>
                    <StatusActionButton onClick={() => void setItemStatus(item.id, "excluded")}>Exclude</StatusActionButton>
                    <StatusActionButton onClick={() => void setItemStatus(item.id, "tax_agent_review")}>Tax Agent Review</StatusActionButton>
                  </div>
                </article>
              ))}
              {reviewItems.length === 0 && <p className="text-xs text-slate-500">No items for this filter yet.</p>}
            </div>
          </div>
        )}

        {activeNav === "Issues" && (
          <div className="space-y-2 text-sm text-slate-600" data-testid="issues-placeholder">
            <p>No dedicated issue engine yet.</p>
            <p>Items marked Tax Agent Review will appear here.</p>
            <p>Current tax agent review count: {reviewSummary?.tax_agent_review ?? 0}</p>
          </div>
        )}

        {activeNav === "Review Pack" && (
          <div className="space-y-2 text-sm text-slate-600" data-testid="review-pack-panel">
            <p>Review pack is {reviewSummary?.ready_for_export ? "ready" : "not ready"}.</p>
            {!reviewSummary?.ready_for_export &&
              (reviewSummary?.blocking_reasons?.length ? (
                <ul className="list-disc pl-5 text-xs text-slate-500">
                  {reviewSummary.blocking_reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              ) : null)}
          </div>
        )}

        {activeNav !== "Dashboard" && activeNav !== "Review Items" && activeNav !== "Issues" && activeNav !== "Review Pack" && (
          <div className="space-y-3 text-sm text-slate-600">
            <p>{activeNav} section shell is active. Existing workflow remains available while route protection is phased in.</p>
            <LinkButton href={workspacePath("documents")}>Go to current workflow</LinkButton>
          </div>
        )}
      </section>

      <aside className="col-span-12 rounded-xl border border-slate-200 bg-white p-4 md:col-span-3">
        <h3 className="text-sm font-semibold text-slate-800">Privacy</h3>
        <div className="mt-3 space-y-2 rounded-lg border border-slate-100 bg-slate-50 p-3 text-xs text-slate-600">
          <p>Your documents stay local by default.</p>
          <p>Cloud AI is off unless explicitly enabled.</p>
          <p>Encrypted exports are planned for review packs.</p>
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

function LinkButton({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="inline-flex rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50">
      {children}
    </Link>
  );
}

function StatusActionButton({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button onClick={onClick} className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700">
      {children}
    </button>
  );
}
