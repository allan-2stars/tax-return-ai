"use client";

import type { TaxItem } from "@/lib/api";

export function ReviewList({
  items,
  onToggleReview,
  onDelete,
}: {
  items: TaxItem[];
  onToggleReview?: (id: string, needsReview: boolean) => void;
  onDelete?: (id: string) => void;
}) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic">No items to review.</p>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item) => {
        const needsReview = item.needs_review;
        const bgClass = needsReview
          ? "border-l-4 border-l-ato-yellow-border bg-yellow-50"
          : "border-l-4 border-l-green-400 bg-white";
        const typeBadge = item.item_type === "income" ? "text-green-700" : "text-blue-700";

        return (
          <div key={item.id} className={`p-3 border border-gray-200 rounded ${bgClass}`}>
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-xs font-semibold uppercase ${typeBadge}`}>
                    {item.item_type}
                  </span>
                  <span className="font-medium text-sm">{item.category}</span>
                  {item.amount !== null && (
                    <span className="text-sm font-semibold">
                      ${item.amount.toFixed(2)}
                    </span>
                  )}
                  <span className="text-xs text-gray-400">
                    confidence: {(item.confidence * 100).toFixed(0)}%
                  </span>
                  {item.ato_reference_hint && (
                    <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">
                      {item.ato_reference_hint}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600 mt-1">{item.description}</p>
                {item.needs_review && item.review_reason && (
                  <p className="text-xs text-ato-red mt-1">
                    ⚠ {item.review_reason}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {onToggleReview && (
                  <button
                    onClick={() => onToggleReview(item.id, !item.needs_review)}
                    className={`px-2 py-1 text-xs rounded ${
                      item.needs_review
                        ? "bg-green-100 text-green-800 hover:bg-green-200"
                        : "bg-yellow-100 text-yellow-800 hover:bg-yellow-200"
                    }`}
                  >
                    {item.needs_review ? "Approve" : "Flag"}
                  </button>
                )}
                {onDelete && (
                  <button
                    onClick={() => onDelete(item.id)}
                    className="px-2 py-1 text-xs rounded bg-red-50 text-red-600 hover:bg-red-100"
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
