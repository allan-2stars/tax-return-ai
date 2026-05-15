"use client";

import { useEffect, useState, useCallback } from "react";
import type { Document, DocumentPage } from "@/lib/api";
import { api } from "@/lib/api";

export function DocumentPreview({
  document: doc,
  onClose,
}: {
  document: Document;
  onClose: () => void;
}) {
  const [pages, setPages] = useState<DocumentPage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPage, setSelectedPage] = useState<number | null>(null);

  const loadPages = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.getDocumentPages(doc.id);
      setPages(result);
      if (result.length > 0) setSelectedPage(result[0].page_number);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load pages");
    } finally {
      setLoading(false);
    }
  }, [doc.id]);

  useEffect(() => {
    loadPages();
  }, [loadPages]);

  const currentPage = pages.find((p) => p.page_number === selectedPage);
  const statusColor: Record<string, string> = {
    classified: "text-green-600 bg-green-50",
    processed: "text-green-600 bg-green-50",
    needs_review: "text-yellow-600 bg-yellow-50",
    duplicate_detected: "text-yellow-600 bg-yellow-50",
    classification_failed: "text-red-600 bg-red-50",
    failed: "text-red-600 bg-red-50",
    uploaded: "text-blue-600 bg-blue-50",
    stored: "text-blue-600 bg-blue-50",
    text_extracted: "text-blue-600 bg-blue-50",
    items_detected: "text-blue-600 bg-blue-50",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <div className="min-w-0 flex-1">
            <h2 className="text-sm font-semibold text-gray-800 truncate">
              {doc.original_filename}
            </h2>
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
              <span className={`px-1.5 py-0.5 rounded ${statusColor[doc.status] || "text-gray-600 bg-gray-50"}`}>
                {doc.status}
              </span>
              <span>{doc.mime_type}</span>
              {doc.file_size_bytes !== null && (
                <span>{(doc.file_size_bytes / 1024).toFixed(1)} KB</span>
              )}
              {doc.category && <span className="capitalize">{doc.category}</span>}
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-4 text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            &times;
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading && (
            <div className="space-y-2">
              <div className="h-4 bg-gray-100 rounded animate-pulse w-3/4" />
              <div className="h-4 bg-gray-100 rounded animate-pulse w-1/2" />
              <div className="h-20 bg-gray-100 rounded animate-pulse mt-4" />
            </div>
          )}
          {error && (
            <p className="text-sm text-red-600 bg-red-50 p-3 rounded">{error}</p>
          )}
          {!loading && !error && pages.length === 0 && (
            <p className="text-sm text-gray-400 italic">
              No OCR text extracted for this document.
            </p>
          )}
          {!loading && !error && pages.length > 0 && (
            <div className="space-y-3">
              {/* Page tabs */}
              {pages.length > 1 && (
                <div className="flex gap-1 border-b border-gray-200 pb-2">
                  {pages.map((p) => (
                    <button
                      key={p.page_number}
                      onClick={() => setSelectedPage(p.page_number)}
                      className={`px-3 py-1 text-xs font-medium rounded-t ${
                        selectedPage === p.page_number
                          ? "bg-ato-blue text-white"
                          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                    >
                      Page {p.page_number}
                    </button>
                  ))}
                </div>
              )}
              {currentPage && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>
                      Method: <span className="font-medium">{currentPage.ocr_method || "unknown"}</span>
                    </span>
                    <span>
                      Confidence:{" "}
                      <span className="font-medium">
                        {currentPage.confidence != null
                          ? `${Math.round(currentPage.confidence * 100)}%`
                          : "N/A"}
                      </span>
                    </span>
                  </div>
                  <pre className="text-xs text-gray-700 bg-gray-50 p-3 rounded border border-gray-200 whitespace-pre-wrap max-h-96 overflow-y-auto leading-relaxed">
                    {currentPage.text || (
                      <span className="text-gray-400 italic">No text on this page</span>
                    )}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-gray-200 text-xs text-gray-400 flex justify-between items-center">
          <span>
            {pages.length > 0
              ? `${pages.length} page${pages.length !== 1 ? "s" : ""}`
              : "No pages loaded"}
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-sm font-medium text-white bg-ato-blue rounded hover:bg-blue-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
