"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { api, type ComplianceResult, type ComplianceItem } from "@/lib/api";
import { SkeletonCard, SkeletonTable } from "@/components/Skeleton";

// ── Helpers ────────────────────────────────────────────────────────────────

const riskBadge = (level: string) => {
  const colors: Record<string, string> = {
    low: "bg-green-100 text-green-700",
    medium: "bg-yellow-100 text-yellow-700",
    high: "bg-red-100 text-red-700",
  };
  return colors[level] || "bg-gray-100 text-gray-600";
};

const evidenceBadge = (status: string) => {
  const colors: Record<string, string> = {
    complete: "bg-green-100 text-green-700",
    partial: "bg-yellow-100 text-yellow-700",
    missing_or_incomplete: "bg-red-100 text-red-700",
  };
  return colors[status] || "bg-gray-100 text-gray-600";
};

const reviewStatusBadge = (status: string) => {
  const colors: Record<string, string> = {
    completed: "bg-green-100 text-green-700",
    in_progress: "bg-blue-100 text-blue-700",
    blocked: "bg-red-100 text-red-700",
  };
  return colors[status] || "bg-gray-100 text-gray-600";
};

const reviewStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    completed: "Completed",
    in_progress: "In Progress",
    blocked: "Blocked",
  };
  return labels[status] || status;
};

// ── CompliantPanel ─────────────────────────────────────────────────────────

export function CompliancePanel({ sessionId }: { sessionId: string }) {
  const [data, setData] = useState<ComplianceResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const fetchCompliance = useCallback(() => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    api
      .getCompliance(sessionId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sessionId]);

  useEffect(() => {
    fetchCompliance();
  }, [fetchCompliance]);

  const filteredItems = useMemo(() => {
    if (!data) return [];
    let items = data.items;
    switch (filter) {
      case "low":
        return items.filter((i) => i.risk_level === "low");
      case "medium":
        return items.filter((i) => i.risk_level === "medium");
      case "high":
        return items.filter((i) => i.risk_level === "high");
      case "tax_agent":
        return items.filter((i) => i.requires_tax_agent);
      default:
        return items;
    }
  }, [data, filter]);

  // ── Loading state ────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="space-y-4">
        <SkeletonCard />
        <SkeletonTable />
      </div>
    );
  }

  // ── Error state ──────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-red-700">Compliance check failed</p>
            <p className="text-xs text-red-600 mt-1">{error}</p>
          </div>
          <button
            onClick={fetchCompliance}
            className="text-xs px-3 py-1.5 bg-red-100 text-red-700 rounded hover:bg-red-200 font-medium"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ── Empty state ──────────────────────────────────────────────────────
  if (!data) {
    return (
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-sm text-yellow-700">No compliance data available.</p>
      </div>
    );
  }

  const { summary, items, review_status, export_readiness, unresolved_questions, tax_agent_review_triggers } = data;
  const totalRisk = summary.risk_counts.low + summary.risk_counts.medium + summary.risk_counts.high || 1;

  // ── Filter buttons ───────────────────────────────────────────────────
  const filterButtons = [
    { key: "all", label: `All (${items.length})` },
    { key: "low", label: `Low Risk (${summary.risk_counts.low})` },
    { key: "medium", label: `Medium Risk (${summary.risk_counts.medium})` },
    { key: "high", label: `High Risk (${summary.risk_counts.high})` },
    { key: "tax_agent", label: `Tax Agent Required (${items.filter((i) => i.requires_tax_agent).length})` },
  ];

  return (
    <div className="space-y-4">
      {/* Summary Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700">Compliance Review Summary</h3>
          <span
            className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${reviewStatusBadge(review_status)}`}
          >
            {reviewStatusLabel(review_status)}
          </span>
        </div>

        {/* Risk heatmap bar */}
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Risk Distribution</p>
          <div className="flex h-5 rounded overflow-hidden text-[10px] font-medium text-white">
            {summary.risk_counts.low > 0 && (
              <div
                className="bg-green-500 flex items-center justify-center"
                style={{ width: `${(summary.risk_counts.low / totalRisk) * 100}%` }}
              >
                {summary.risk_counts.low}
              </div>
            )}
            {summary.risk_counts.medium > 0 && (
              <div
                className="bg-yellow-500 flex items-center justify-center"
                style={{ width: `${(summary.risk_counts.medium / totalRisk) * 100}%` }}
              >
                {summary.risk_counts.medium}
              </div>
            )}
            {summary.risk_counts.high > 0 && (
              <div
                className="bg-red-500 flex items-center justify-center"
                style={{ width: `${(summary.risk_counts.high / totalRisk) * 100}%` }}
              >
                {summary.risk_counts.high}
              </div>
            )}
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="bg-gray-50 rounded p-2">
            <span className="text-gray-400 block">Documents Reviewed</span>
            <span className="text-gray-800 font-semibold text-sm">{summary.documents_reviewed}</span>
          </div>
          <div className="bg-gray-50 rounded p-2">
            <span className="text-gray-400 block">Evidence Complete</span>
            <span className="text-green-600 font-semibold text-sm">{summary.evidence_complete}</span>
          </div>
          <div className="bg-gray-50 rounded p-2">
            <span className="text-gray-400 block">Evidence Incomplete</span>
            <span className="text-ato-red font-semibold text-sm">{summary.evidence_incomplete}</span>
          </div>
          <div className="bg-gray-50 rounded p-2">
            <span className="text-gray-400 block">FY Date Warnings</span>
            <span className={`font-semibold text-sm ${summary.fy_date_warnings > 0 ? "text-ato-red" : "text-green-600"}`}>
              {summary.fy_date_warnings}
            </span>
          </div>
        </div>

        {/* Export readiness */}
        <div className="text-xs">
          <span className="text-gray-400">Export Readiness: </span>
          <span
            className={`font-medium ${
              export_readiness.status === "ready_for_human_review_export"
                ? "text-green-600"
                : "text-yellow-600"
            }`}
          >
            {export_readiness.status.replace(/_/g, " ")}
          </span>
          {export_readiness.reason && (
            <span className="text-gray-400 ml-1">&mdash; {export_readiness.reason}</span>
          )}
        </div>
      </div>

      {/* Filter buttons */}
      <div className="flex flex-wrap gap-2">
        {filterButtons.map((btn) => (
          <button
            key={btn.key}
            onClick={() => setFilter(btn.key)}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              filter === btn.key
                ? "bg-ato-blue text-white border-ato-blue"
                : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
            }`}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* Items table */}
      {filteredItems.length === 0 ? (
        <p className="text-sm text-gray-400 italic">No items to review.</p>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 text-left border-b border-gray-200">
                <th className="py-2.5 px-3 text-xs font-medium text-gray-500">Category</th>
                <th className="py-2.5 px-3 text-xs font-medium text-gray-500">Risk Level</th>
                <th className="py-2.5 px-3 text-xs font-medium text-gray-500">Evidence</th>
                <th className="py-2.5 px-3 text-xs font-medium text-gray-500">Tax Agent</th>
                <th className="py-2.5 px-3 text-xs font-medium text-gray-500">Findings</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item: ComplianceItem) => (
                <tr
                  key={item.item_id}
                  className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                >
                  <td className="py-2.5 px-3">
                    <span className="text-xs font-medium text-gray-700 capitalize">
                      {item.category.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${riskBadge(
                        item.risk_level
                      )}`}
                    >
                      {item.risk_level}
                    </span>
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${evidenceBadge(
                        item.evidence_status
                      )}`}
                    >
                      {item.evidence_status.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    {item.requires_tax_agent ? (
                      <span className="text-red-500 text-sm" title={item.tax_agent_reason ?? undefined}>
                        ⚑
                      </span>
                    ) : (
                      <span className="text-gray-300 text-sm">—</span>
                    )}
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="flex flex-wrap gap-1">
                      {item.findings.length > 0 ? (
                        item.findings.map((f, i) => (
                          <span
                            key={i}
                            className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded"
                          >
                            {f}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-gray-400 italic">No findings</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Unresolved questions */}
      {unresolved_questions.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <p className="text-xs font-medium text-yellow-700 mb-1">
            Unresolved Questions ({unresolved_questions.length})
          </p>
          <ul className="list-disc pl-4 space-y-0.5">
            {unresolved_questions.map((q, i) => (
              <li key={i} className="text-xs text-yellow-600">
                {q}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Tax agent review triggers */}
      {tax_agent_review_triggers.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <p className="text-xs font-medium text-red-700 mb-1">
            Tax Agent Review Triggers ({tax_agent_review_triggers.length})
          </p>
          <ul className="list-disc pl-4 space-y-0.5">
            {tax_agent_review_triggers.map((t, i) => (
              <li key={i} className="text-xs text-red-600">
                {t}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
