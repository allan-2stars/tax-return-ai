"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type ExportRecord } from "@/lib/api";
import { ExportButton } from "./ExportButton";

export function ExportPanel({ sessionId }: { sessionId: string }) {
  const [history, setHistory] = useState<ExportRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const loadHistory = useCallback(() => {
    if (!sessionId) return;
    setLoading(true);
    api.getExportHistory(sessionId)
      .then(setHistory)
      .catch(() => setHistory([]))
      .finally(() => setLoading(false));
  }, [sessionId]);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        Generate a reviewable export package. This is a draft data summary
        &mdash; NOT a tax return and NOT for lodgement.
      </p>
      <div className="flex items-center gap-2">
        <ExportButton sessionId={sessionId} />
        <button
          onClick={() => api.exportSessionCsv(sessionId)}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50"
        >
          Export CSV
        </button>
      </div>
      {history.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Export History ({history.length})
          </h3>
          <div className="space-y-1">
            {history.map((rec) => (
              <div key={rec.id} className="flex items-center gap-3 text-xs text-gray-600 px-3 py-2 bg-white border border-gray-200 rounded">
                <span className="font-medium uppercase">{rec.format}</span>
                <span className="text-gray-400">
                  {rec.item_count} items
                  {rec.total_amount != null && ` — $${rec.total_amount.toFixed(2)}`}
                </span>
                <span className="text-gray-400 ml-auto">
                  {new Date(rec.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      {!loading && history.length === 0 && (
        <p className="text-xs text-gray-400 italic">No previous exports.</p>
      )}
    </div>
  );
}
