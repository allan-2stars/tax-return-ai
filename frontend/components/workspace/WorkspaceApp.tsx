"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type Session, type SessionStats } from "@/lib/api";
import {
  type AppAuthState,
  createMasterPassword,
  expireSessionNow,
  getInitialAuthState,
  getRecoveryKey,
  confirmRecoveryKey,
  lockWorkspace,
  unlockWorkspace,
} from "@/lib/mockAuth";
import { MOCK_TAX_YEARS } from "@/lib/mockWorkspaces";

type NavItem = "Dashboard" | "Documents" | "Review Items" | "Issues" | "Review Pack" | "Settings";

const NAV_ITEMS: NavItem[] = ["Dashboard", "Documents", "Review Items", "Issues", "Review Pack", "Settings"];

export function WorkspaceApp() {
  const [authState, setAuthState] = useState<AppAuthState>("UNINITIALIZED");
  const [setupStep, setSetupStep] = useState<"create" | "show_key" | "confirm_key">("create");
  const [password, setPassword] = useState("");
  const [unlockInput, setUnlockInput] = useState("");
  const [confirmInput, setConfirmInput] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [activeNav, setActiveNav] = useState<NavItem>("Dashboard");
  const [selectedTaxYear, setSelectedTaxYear] = useState(MOCK_TAX_YEARS[0].id);

  const [sessions, setSessions] = useState<Session[]>([]);
  const [statsMap, setStatsMap] = useState<Record<string, SessionStats>>({});

  useEffect(() => {
    setAuthState(getInitialAuthState());
  }, []);

  useEffect(() => {
    if (authState !== "UNLOCKED") return;
    api
      .listSessions()
      .then(async (list) => {
        setSessions(list);
        const statResults = await Promise.allSettled(list.map((s) => api.getSessionStats(s.id)));
        const next: Record<string, SessionStats> = {};
        statResults.forEach((r, i) => {
          if (r.status === "fulfilled") next[list[i].id] = r.value;
        });
        setStatsMap(next);
      })
      .catch(() => {
        setSessions([]);
        setStatsMap({});
      });
  }, [authState]);

  const selectedSession = sessions[0];
  const selectedStats = selectedSession ? statsMap[selectedSession.id] : undefined;

  const stepState = useMemo(() => {
    const docs = selectedStats?.document_count ?? 0;
    const reviewed = selectedStats ? selectedStats.total_item_count - selectedStats.needs_review_item_count : 0;
    const needs = selectedStats?.needs_review_item_count ?? 0;

    return {
      documents: docs > 0 ? "ready" : "todo",
      review: docs > 0 ? (needs > 0 ? "in_progress" : reviewed > 0 ? "ready" : "todo") : "blocked",
      issues: docs > 0 ? (needs > 0 ? "in_progress" : "ready") : "blocked",
      pack: docs > 0 && needs === 0 ? "ready" : docs > 0 ? "blocked" : "blocked",
    };
  }, [selectedStats]);

  if (authState === "UNINITIALIZED") {
    return (
      <AuthCard title="Create Master Password" subtitle="Set up your local workspace unlock.">
        {setupStep === "create" && (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (password.length < 8) {
                setMessage("Use at least 8 characters.");
                return;
              }
              createMasterPassword(password);
              setSetupStep("show_key");
              setMessage(null);
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
            <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-sm text-slate-800">{getRecoveryKey()}</div>
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
              if (!confirmRecoveryKey(confirmInput)) {
                setMessage("Recovery key does not match.");
                return;
              }
              setMessage(null);
              setAuthState("LOCKED");
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
      <AuthCard title="Unlock Workspace" subtitle="Enter master password to access documents.">
        <form
          className="space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setAuthState("UNLOCKING");
            const ok = await unlockWorkspace(unlockInput);
            if (!ok) {
              setAuthState("LOCKED");
              setMessage("Unable to unlock. Check your password.");
              return;
            }
            setMessage(null);
            setAuthState("UNLOCKED");
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

  if (authState === "UNLOCKING") {
    return <AuthCard title="Unlocking" subtitle="Preparing workspace session..." />;
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
            <p className="text-xs text-slate-500">Secure workspace shell (phase foundation)</p>
          </div>
          <div className="flex items-center gap-2" data-testid="tax-year-selector">
            <label htmlFor="tax-year" className="text-xs text-slate-500">
              Tax Year
            </label>
            <select
              id="tax-year"
              value={selectedTaxYear}
              onChange={(e) => setSelectedTaxYear(e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs"
            >
              {MOCK_TAX_YEARS.map((y) => (
                <option key={y.id} value={y.id}>
                  {y.label}
                </option>
              ))}
            </select>
          </div>
        </header>

        {activeNav === "Dashboard" && (
          <div className="space-y-3" data-testid="guided-steps">
            <GuidedStep
              title="Step 1: Add documents"
              status={stepState.documents}
              description="Upload payslips, statements, and receipts for this tax year."
              action={selectedSession ? <LinkButton href={`/session/${selectedSession.id}`}>Open Documents</LinkButton> : <span className="text-xs text-slate-400">Create a session first</span>}
            />
            <GuidedStep
              title="Step 2: Review extracted items"
              status={stepState.review}
              description="Confirm inferred income and deduction items before they are included in the review pack."
              action={selectedSession ? <LinkButton href={`/session/${selectedSession.id}`}>Open Review Items</LinkButton> : null}
            />
            <GuidedStep
              title="Step 3: Resolve issues"
              status={stepState.issues}
              description="Resolve items marked Needs Review, Excluded, or Tax Agent Review."
              action={selectedSession ? <LinkButton href={`/session/${selectedSession.id}`}>Open Issues</LinkButton> : null}
            />
            <GuidedStep
              title="Step 4: Generate review pack"
              status={stepState.pack}
              description="Export the current workspace for human review and handoff."
              action={selectedSession ? <LinkButton href={`/session/${selectedSession.id}`}>Open Review Pack</LinkButton> : null}
            />
          </div>
        )}

        {activeNav !== "Dashboard" && (
          <div className="space-y-3 text-sm text-slate-600">
            <p>
              {activeNav} workspace section is now available in the new shell. Existing functionality remains available in
              the current session page.
            </p>
            {selectedSession ? (
              <LinkButton href={`/session/${selectedSession.id}`}>Go to current {activeNav}</LinkButton>
            ) : (
              <p className="text-xs text-slate-400">No active session found. Create one on the existing home page.</p>
            )}
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
            onClick={() => {
              lockWorkspace();
              setAuthState("LOCKED");
            }}
          >
            Lock workspace
          </button>
          <button
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs"
            onClick={() => {
              expireSessionNow();
              setAuthState("SESSION_EXPIRED");
            }}
          >
            Simulate session expiry
          </button>
          <button className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs" onClick={() => setAuthState("LOCKED")}>
            Return to unlock
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
      <p className="mt-5 text-xs text-slate-400">
        TODO: Temporary auth placeholder only. Replace with backend security implementation before production.
      </p>
    </div>
  );
}

function GuidedStep({
  title,
  description,
  status,
  action,
}: {
  title: string;
  description: string;
  status: "todo" | "in_progress" | "ready" | "blocked";
  action: React.ReactNode;
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
      <div className={`mt-2 ${status === "blocked" ? "opacity-45 pointer-events-none" : ""}`}>{action}</div>
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
