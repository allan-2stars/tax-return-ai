"use client";

import type { Session, SessionStats } from "@/lib/api";

export function SessionCard({
  session,
  stats,
  onSelect,
}: {
  session: Session;
  stats?: SessionStats;
  onSelect: (id: string) => void;
}) {
  const fy = session.financial_year;
  const statusColor =
    session.status === "active"
      ? "bg-green-100 text-green-800"
      : session.status === "completed"
      ? "bg-blue-100 text-blue-800"
      : "bg-gray-100 text-gray-800";

  const hasStats = stats && stats.total_item_count > 0;
  const hasDocs = stats && stats.document_count > 0;

  return (
    <button
      onClick={() => onSelect(session.id)}
      className="w-full text-left p-4 bg-white border border-gray-200 rounded-lg hover:border-ato-blue hover:shadow-sm transition-all"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="font-medium text-gray-900 truncate">
            {session.title}
          </h3>
          {session.notes && (
            <p className="text-sm text-gray-500 mt-1">{session.notes}</p>
          )}
        </div>
        <span
          className={`shrink-0 px-2 py-0.5 text-xs font-medium rounded-full ${statusColor}`}
        >
          {session.status}
        </span>
      </div>
      <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
        <span>FY {fy}</span>
        <span>Created: {new Date(session.created_at).toLocaleDateString()}</span>
      </div>
      {(hasStats || hasDocs) && (
        <div className="flex items-center gap-3 mt-2 text-xs">
          <span className="text-gray-500">
            {stats!.document_count} document{stats!.document_count !== 1 ? "s" : ""}
            {stats!.classified_document_count > 0 && (
              <> &mdash; {stats!.classified_document_count} classified</>
            )}
          </span>
          {hasStats && (
            <>
              <span className="text-green-700">
                {stats!.income_item_count} income
              </span>
              <span className="text-blue-700">
                {stats!.deduction_item_count} deduction
              </span>
              {stats!.needs_review_item_count > 0 && (
                <span className="text-yellow-700">
                  {stats!.needs_review_item_count} needs review
                </span>
              )}
            </>
          )}
        </div>
      )}
    </button>
  );
}
