"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, type Session, type Document, type TaxItem, type UploadResponse, type Job, type DocumentPage } from "@/lib/api";
import { DocumentUploader } from "@/components/DocumentUploader";
import { ReviewList } from "@/components/ReviewList";
import { ExportPanel } from "@/components/ExportPanel";
import { ItemTable } from "@/components/ItemTable";
import { DocumentPreview } from "@/components/DocumentPreview";
import { CompliancePanel } from "@/components/CompliancePanel";
import { SkeletonCard, SkeletonTable, SkeletonText } from "@/components/Skeleton";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const sessionId = id;

  const [session, setSession] = useState<Session | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [items, setItems] = useState<TaxItem[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"items" | "review" | "export" | "jobs" | "compliance">("items");
  const [previewDocument, setPreviewDocument] = useState<Document | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);

  const loadData = useCallback(() => {
    if (!sessionId) return;
    setLoading(true);
    Promise.all([
      api.getSession(sessionId).catch(() => null),
      api.listDocuments(sessionId).catch(() => []),
      api.listItems(sessionId).catch(() => []),
      api.listJobs(sessionId).catch(() => []),
    ])
      .then(([s, docs, itms, js]) => {
        setSession(s);
        setDocuments(docs);
        setItems(itms);
        setJobs(js);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sessionId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleUploaded = () => {
    loadData();
  };

  const handleToggleReview = async (itemId: string, needsReview: boolean) => {
    try {
      await api.reviewItem(itemId, needsReview, needsReview ? "Flagged by user" : undefined);
      loadData();
    } catch (err) {
      console.error("Review toggle failed:", err);
    }
  };

  const handleDelete = async (itemId: string) => {
    if (!confirm("Delete this item?")) return;
    try {
      await api.deleteItem(itemId);
      loadData();
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  const handleUpdateItem = async (itemId: string, data: { amount?: number | null; description?: string }) => {
    setUpdateError(null);
    try {
      await api.updateItem(itemId, data);
      loadData();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to update item";
      setUpdateError(msg);
      throw err;
    }
  };

  // ── Loading state ────────────────────────────────────────────────────
  if (loading && !session) {
    return (
      <div className="space-y-4">
        <SkeletonCard />
        <SkeletonTable />
      </div>
    );
  }

  if (error && !session) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-sm text-ato-red">{error}</p>
        <button
          onClick={loadData}
          className="mt-2 text-xs px-3 py-1.5 bg-red-100 text-red-700 rounded hover:bg-red-200"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-sm text-yellow-700">Session not found.</p>
        <button
          onClick={() => router.push("/")}
          className="mt-2 text-xs px-3 py-1.5 bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200"
        >
          Back to sessions
        </button>
      </div>
    );
  }

  const needsReviewItems = items.filter((i) => i.needs_review);
  const approvedItems = items.filter((i) => !i.needs_review);

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      classified: "bg-green-100 text-green-700",
      processed: "bg-green-100 text-green-700",
      needs_review: "bg-yellow-100 text-yellow-700",
      duplicate_detected: "bg-yellow-100 text-yellow-700",
      classification_failed: "bg-red-100 text-red-700",
      failed: "bg-red-100 text-red-700",
      uploaded: "bg-blue-100 text-blue-700",
      stored: "bg-blue-100 text-blue-700",
      text_extracted: "bg-blue-100 text-blue-700",
      items_detected: "bg-blue-100 text-blue-700",
      classification_pending: "bg-blue-100 text-blue-700",
    };
    return colors[status] || "bg-gray-100 text-gray-600";
  };

  const jobStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      succeeded: "bg-green-100 text-green-700",
      failed: "bg-red-100 text-red-700",
      running: "bg-blue-100 text-blue-700",
      queued: "bg-gray-100 text-gray-600",
      cancelled: "bg-gray-100 text-gray-600",
      retrying: "bg-yellow-100 text-yellow-700",
    };
    return colors[status] || "bg-gray-100 text-gray-600";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => router.push("/")}
            className="text-xs text-gray-400 hover:text-gray-600 mb-1 block"
          >
            &larr; Back to sessions
          </button>
          <h1 className="text-xl font-semibold text-gray-800">
            {session.title}
          </h1>
          <p className="text-sm text-gray-500">
            FY {session.financial_year} &mdash;{" "}
            {session.status} &mdash;{" "}
            {documents.length} documents, {items.length} items
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={async () => {
              const newStatus = session.status === "archived" ? "active" : "archived";
              await api.updateSession(session.id, { status: newStatus });
              loadData();
            }}
            className={`px-3 py-1 text-xs font-medium rounded ${
              session.status === "archived"
                ? "text-green-700 bg-green-100 hover:bg-green-200"
                : "text-gray-600 bg-gray-100 hover:bg-gray-200"
            }`}
          >
            {session.status === "archived" ? "Unarchive" : "Archive"}
          </button>
          <button
            onClick={async () => {
              if (!confirm(`Delete session "${session.title}" and all its data?`)) return;
              await api.deleteSession(session.id);
              router.push("/");
            }}
            className="px-3 py-1 text-xs font-medium text-red-700 bg-red-100 rounded hover:bg-red-200"
          >
            Delete
          </button>
          <span className="text-xs text-gray-400">
            {new Date(session.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      {/* Upload */}
      <div className="p-4 bg-white border border-gray-200 rounded-lg">
        <h2 className="text-sm font-medium text-gray-700 mb-2">Upload Document</h2>
        <DocumentUploader
          sessionId={sessionId}
          financialYear={session.financial_year}
          onUploaded={handleUploaded}
        />
      </div>

      {/* Update error banner */}
      {updateError && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {updateError}
          <button
            onClick={() => setUpdateError(null)}
            className="ml-2 text-red-500 hover:text-red-700"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-200 gap-4 overflow-x-auto">
        {(["items", "review", "export", "jobs", "compliance"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              activeTab === tab
                ? "border-ato-blue text-ato-blue"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab === "items" && `All Items (${items.length})`}
            {tab === "review" && `Needs Review (${needsReviewItems.length})`}
            {tab === "export" && "Export"}
            {tab === "jobs" && `Jobs (${jobs.length})`}
            {tab === "compliance" && "Compliance"}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "items" && (
        <ErrorBoundary
          onRetry={loadData}
          fallback={
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">Failed to load items. Please try again.</p>
              <button
                onClick={loadData}
                className="mt-2 text-xs px-3 py-1.5 bg-red-100 text-red-700 rounded hover:bg-red-200"
              >
                Retry
              </button>
            </div>
          }
        >
          <ItemTable
            items={items}
            onToggleReview={handleToggleReview}
            onDelete={handleDelete}
            onUpdateItem={handleUpdateItem}
          />
        </ErrorBoundary>
      )}

      {activeTab === "review" && (
        <div className="space-y-4">
          {needsReviewItems.length === 0 ? (
            <p className="text-sm text-green-700 bg-green-50 p-3 rounded">
              ✓ All items have been reviewed.
            </p>
          ) : (
            <>
              <p className="text-sm text-yellow-700 bg-yellow-50 p-3 rounded">
                {needsReviewItems.length} item(s) need your review. Review each one and
                approve or flag for further attention.
              </p>
              <ErrorBoundary onRetry={loadData}>
                <ReviewList
                  items={needsReviewItems}
                  onToggleReview={handleToggleReview}
                  onDelete={handleDelete}
                />
              </ErrorBoundary>
            </>
          )}
        </div>
      )}

      {activeTab === "export" && (
        <ExportPanel sessionId={sessionId} />
      )}

      {activeTab === "jobs" && (
        <div className="space-y-2">
          {jobs.length === 0 && (
            <p className="text-sm text-gray-400 italic">No jobs yet.</p>
          )}
          {jobs.map((j) => (
            <div
              key={j.id}
              className="flex items-center gap-3 text-xs text-gray-600 px-3 py-2 bg-white border border-gray-200 rounded"
            >
              <span className={`px-1.5 py-0.5 rounded-full ${jobStatusBadge(j.status)}`}>
                {j.status}
              </span>
              <span className="font-medium capitalize">{j.job_type}</span>
              {j.progress_message && (
                <span className="text-gray-400 truncate max-w-[200px]">
                  {j.progress_message}
                </span>
              )}
              {j.started_at && (
                <span className="text-gray-400 ml-auto">
                  {new Date(j.started_at).toLocaleTimeString()}
                </span>
              )}
              {j.error_message && (
                <span className="text-ato-red truncate max-w-[200px]" title={j.error_message}>
                  {j.error_message}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {activeTab === "compliance" && (
        <ErrorBoundary onRetry={loadData}>
          <CompliancePanel sessionId={sessionId} />
        </ErrorBoundary>
      )}

      {/* Documents list */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h2 className="text-sm font-medium text-gray-700 mb-3">
          Source Documents ({documents.length})
        </h2>
        <div className="space-y-1">
          {documents.length === 0 && (
            <p className="text-xs text-gray-400 italic">No documents uploaded yet.</p>
          )}
          {documents.map((d) => (
            <div
              key={d.id}
              className="flex items-center gap-3 text-xs text-gray-600 px-3 py-2 bg-gray-50 rounded hover:bg-gray-100 transition-colors group"
            >
              <button
                onClick={() => setPreviewDocument(d)}
                className="font-medium text-ato-blue hover:underline truncate max-w-[200px] cursor-pointer flex-1 min-w-0 text-left"
                title="Click to preview OCR text"
              >
                {d.original_filename}
              </button>
              <span className={`px-1.5 py-0.5 rounded-full ${statusBadge(d.status)} shrink-0`}>
                {d.status.replace(/_/g, " ")}
              </span>
              {d.status === "duplicate_detected" && (
                <span className="text-yellow-600 shrink-0">(duplicate)</span>
              )}
              {d.status === "classification_failed" && (
                <button
                  onClick={async () => {
                    try {
                      await api.updateDocument(d.id, { status: "uploaded" });
                      loadData();
                    } catch (err) {
                      console.error("Reclassify failed:", err);
                    }
                  }}
                  className="text-xs text-ato-blue hover:underline shrink-0"
                >
                  Retry
                </button>
              )}
              {d.status === "duplicate_detected" && (
                <button
                  onClick={async () => {
                    if (!confirm(`Delete duplicate document "${d.original_filename}"?`)) return;
                    try {
                      await api.deleteDocument(d.id);
                      loadData();
                    } catch (err) {
                      console.error("Delete failed:", err);
                    }
                  }}
                  className="text-xs text-red-600 hover:underline shrink-0"
                >
                  Delete
                </button>
              )}
              {d.file_size_bytes !== null && (
                <span className="text-gray-400 shrink-0">
                  {(d.file_size_bytes / 1024).toFixed(1)} KB
                </span>
              )}
              <button
                onClick={async () => {
                  if (!confirm(`Delete document "${d.original_filename}"? This will also remove its classified items.`)) return;
                  try {
                    await api.deleteDocument(d.id);
                    loadData();
                  } catch (err) {
                    console.error("Delete document failed:", err);
                  }
                }}
                className="text-xs text-red-400 hover:text-red-600 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                title="Delete document"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Document Preview Modal */}
      {previewDocument && (
        <DocumentPreview
          document={previewDocument}
          onClose={() => setPreviewDocument(null)}
        />
      )}
    </div>
  );
}
