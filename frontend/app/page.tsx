"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Session, type SessionStats } from "@/lib/api";
import { SessionCard } from "@/components/SessionCard";

export default function Home() {
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [statsMap, setStatsMap] = useState<Record<string, SessionStats>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newFY, setNewFY] = useState("2025-2026");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [healthMsg, setHealthMsg] = useState<string | null>(null);

  const loadSessions = async () => {
    try {
      const sessions = await api.listSessions();
      setSessions(sessions);
      const statsResults = await Promise.allSettled(
        sessions.map((s) => api.getSessionStats(s.id))
      );
      const stats: Record<string, SessionStats> = {};
      statsResults.forEach((result, i) => {
        if (result.status === "fulfilled") {
          stats[sessions[i].id] = result.value;
        }
      });
      setStatsMap(stats);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load sessions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Health check
    api.health().then((h) => setHealthMsg(h.status)).catch(() => setHealthMsg("unreachable"));
    loadSessions();
  }, []);

  const createSession = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const session = await api.createSession({
        title: newTitle,
        financial_year: newFY,
      });
      router.push(`/session/${session.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
    }
  };

  const startEdit = (session: Session) => {
    setEditingId(session.id);
    setEditTitle(session.title);
  };

  const saveEdit = async (sessionId: string) => {
    try {
      const updated = await api.updateSession(sessionId, { title: editTitle });
      setSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? updated : s))
      );
      setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update session");
    }
  };

  const deleteSession = async (sessionId: string) => {
    try {
      await api.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      setConfirmDeleteId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete session");
    }
  };

  if (loading) return <p className="text-gray-500">Loading sessions...</p>;
  if (error)
    return <p className="text-ato-red bg-red-50 p-3 rounded">{error}</p>;

  return (
    <div className="space-y-6">
      {/* Health indicator */}
      <div className="flex items-center gap-4 text-xs text-gray-400">
        <div className="flex items-center gap-1">
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              healthMsg === "ok"
                ? "bg-green-500"
                : healthMsg === "unreachable"
                ? "bg-red-500"
                : "bg-gray-300"
            }`}
          />
          API: {healthMsg ?? "checking..."}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-800">Tax Sessions</h1>
        <button
          onClick={() => setShowNewForm(!showNewForm)}
          className="px-4 py-2 text-sm font-medium text-white bg-ato-blue rounded hover:bg-blue-700"
        >
          {showNewForm ? "Cancel" : "+ New Session"}
        </button>
      </div>

      {showNewForm && (
        <form
          onSubmit={createSession}
          className="p-4 bg-white border border-gray-200 rounded-lg space-y-3"
        >
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Session Title
            </label>
            <input
              type="text"
              name="title"
              required
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="e.g. FY2025-2026 — Individual"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Financial Year
            </label>
            <select
              name="financial_year"
              value={newFY}
              onChange={(e) => setNewFY(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm"
            >
              <option value="2025-2026">2025-2026</option>
              <option value="2024-2025">2024-2025</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={!newTitle.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-ato-green rounded hover:bg-green-700 disabled:opacity-40"
          >
            Create
          </button>
        </form>
      )}

      {sessions.length === 0 ? (
        <p className="text-gray-400 text-sm">
          No sessions yet. Create one to get started.
        </p>
      ) : (
        <div className="grid gap-3">
          {sessions.map((s) => (
            <div key={s.id} className="relative group">
              {editingId === s.id ? (
                <div className="p-4 bg-white border border-ato-blue rounded-lg space-y-2">
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === "Enter") saveEdit(s.id);
                      if (e.key === "Escape") setEditingId(null);
                    }}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => saveEdit(s.id)}
                      className="px-3 py-1 text-xs font-medium text-white bg-ato-blue rounded hover:bg-blue-700"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="px-3 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded hover:bg-gray-200"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <SessionCard
                  session={s}
                  stats={statsMap[s.id]}
                  onSelect={(id) => router.push(`/session/${id}`)}
                />
              )}

              {/* Action buttons — hover */}
              {editingId !== s.id && (
                <div className="absolute top-2 right-2 hidden group-hover:flex gap-1 z-10">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      startEdit(s);
                    }}
                    title="Rename"
                    className="p-1.5 bg-white border border-gray-200 rounded text-gray-500 hover:text-ato-blue hover:border-ato-blue text-xs"
                  >
                    ✏️
                  </button>
                  <button
                    onClick={async (e) => {
                      e.stopPropagation();
                      const newStatus = s.status === "archived" ? "active" : "archived";
                      const updated = await api.updateSession(s.id, { status: newStatus });
                      setSessions((prev) =>
                        prev.map((x) => (x.id === s.id ? updated : x))
                      );
                    }}
                    title={s.status === "archived" ? "Unarchive" : "Archive"}
                    className="p-1.5 bg-white border border-gray-200 rounded text-gray-500 hover:text-ato-blue hover:border-ato-blue text-xs"
                  >
                    {s.status === "archived" ? "📂" : "📦"}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirmDeleteId(s.id);
                    }}
                    title="Delete session"
                    className="p-1.5 bg-white border border-gray-200 rounded text-gray-500 hover:text-red-600 hover:border-red-400 text-xs"
                  >
                    🗑️
                  </button>
                </div>
              )}

              {/* Delete confirmation dialog */}
              {confirmDeleteId === s.id && (
                <div className="absolute inset-0 bg-white/90 border border-red-200 rounded-lg flex items-center justify-center z-20">
                  <div className="text-center space-y-2">
                    <p className="text-sm font-medium text-gray-800">
                      Delete &ldquo;{s.title}&rdquo;?
                    </p>
                    <p className="text-xs text-gray-500">
                      All documents and items will be permanently removed.
                    </p>
                    <div className="flex gap-2 justify-center">
                      <button
                        onClick={() => deleteSession(s.id)}
                        className="px-3 py-1 text-xs font-medium text-white bg-red-600 rounded hover:bg-red-700"
                      >
                        Delete
                      </button>
                      <button
                        onClick={() => setConfirmDeleteId(null)}
                        className="px-3 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded hover:bg-gray-200"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
