"use client";

import { useState } from "react";
import type { TaxItem } from "@/lib/api";

export function ItemTable({
  items,
  onToggleReview,
  onDelete,
  onUpdateItem,
}: {
  items: TaxItem[];
  onToggleReview: (itemId: string, needsReview: boolean) => void;
  onDelete: (itemId: string) => void;
  onUpdateItem: (itemId: string, data: { amount?: number | null; description?: string }) => Promise<void>;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [savingId, setSavingId] = useState<string | null>(null);

  const itemsByType = {
    income: items.filter((i) => i.item_type === "income"),
    deduction: items.filter((i) => i.item_type === "deduction"),
    out_of_scope: items.filter((i) => i.item_type === "out_of_scope"),
    needs_review: items.filter((i) => i.needs_review),
  };

  const handleStartEdit = (item: TaxItem) => {
    setEditingId(item.id);
    setEditValue(item.amount?.toString() ?? "");
  };

  const handleSaveEdit = async (item: TaxItem) => {
    setSavingId(item.id);
    try {
      const val = editValue.trim() === "" ? null : parseFloat(editValue);
      await onUpdateItem(item.id, { amount: isNaN(val as number) ? null : val });
    } finally {
      setEditingId(null);
      setSavingId(null);
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
  };

  const renderItemRow = (item: TaxItem, index: number) => {
    const confPct = item.confidence != null ? Math.round(item.confidence * 100) : null;
    const confColor =
      confPct === null
        ? "text-gray-400"
        : confPct >= 80
          ? "text-green-600"
          : confPct >= 60
            ? "text-yellow-600"
            : "text-red-600";

    return (
      <tr key={item.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
        <td className="py-2.5 px-3 text-xs text-gray-400 w-8">{index + 1}</td>
        <td className="py-2.5 px-3">
          <span className="text-xs font-medium text-gray-700 capitalize">{item.category.replace(/_/g, " ")}</span>
        </td>
        <td className="py-2.5 px-3">
          <span className="text-sm text-gray-800 line-clamp-1">
            {item.description || <span className="text-gray-400 italic">No description</span>}
          </span>
        </td>
        <td className="py-2.5 px-3">
          {editingId === item.id ? (
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-400">$</span>
              <input
                type="number"
                step="0.01"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                className="w-24 border border-blue-300 rounded px-1.5 py-0.5 text-sm text-right"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSaveEdit(item);
                  if (e.key === "Escape") handleCancelEdit();
                }}
              />
              <button
                onClick={() => handleSaveEdit(item)}
                disabled={savingId === item.id}
                className="text-xs text-green-600 hover:text-green-800 px-1"
              >
                {savingId === item.id ? "..." : "✓"}
              </button>
              <button
                onClick={handleCancelEdit}
                className="text-xs text-gray-400 hover:text-gray-600 px-1"
              >
                ✗
              </button>
            </div>
          ) : (
            <button
              onClick={() => handleStartEdit(item)}
              className="text-sm text-gray-800 hover:text-blue-600 hover:underline cursor-pointer text-right w-full"
              title="Click to edit amount"
            >
              {item.amount != null ? `$${item.amount.toFixed(2)}` : <span className="text-gray-400 italic">—</span>}
            </button>
          )}
        </td>
        <td className="py-2.5 px-3">
          <span className={`text-xs font-medium ${confColor}`}>
            {confPct !== null ? `${confPct}%` : "—"}
          </span>
        </td>
        <td className="py-2.5 px-3">
          <span
            className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${
              item.needs_review
                ? "bg-yellow-100 text-yellow-700"
                : "bg-green-100 text-green-700"
            }`}
          >
            {item.needs_review ? "Review" : "Approved"}
          </span>
        </td>
        <td className="py-2.5 px-3">
          <div className="flex items-center gap-1">
            <button
              onClick={() => onToggleReview(item.id, !item.needs_review)}
              className={`text-xs px-2 py-1 rounded ${
                item.needs_review
                  ? "bg-green-100 text-green-700 hover:bg-green-200"
                  : "bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
              }`}
              title={item.needs_review ? "Approve item" : "Flag for review"}
            >
              {item.needs_review ? "Approve" : "Flag"}
            </button>
            <button
              onClick={() => onDelete(item.id)}
              className="text-xs px-2 py-1 rounded bg-red-50 text-red-500 hover:bg-red-100"
              title="Delete item"
            >
              Delete
            </button>
          </div>
        </td>
      </tr>
    );
  };

  const renderSection = (title: string, sectionItems: TaxItem[], bgClass: string) => {
    if (sectionItems.length === 0) return null;
    return (
      <div className="mb-4">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3">
          {title} ({sectionItems.length})
        </h3>
        <table className="w-full bg-white rounded-lg border border-gray-200 overflow-hidden">
          <thead>
            <tr className="bg-gray-50 text-left border-b border-gray-200">
              <th className="py-2.5 px-3 text-xs font-medium text-gray-500 w-8">#</th>
              <th className="py-2.5 px-3 text-xs font-medium text-gray-500">Category</th>
              <th className="py-2.5 px-3 text-xs font-medium text-gray-500">Description</th>
              <th className="py-2.5 px-3 text-xs font-medium text-gray-500 text-right">Amount</th>
              <th className="py-2.5 px-3 text-xs font-medium text-gray-500">Confidence</th>
              <th className="py-2.5 px-3 text-xs font-medium text-gray-500">Status</th>
              <th className="py-2.5 px-3 text-xs font-medium text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody>
            {sectionItems.map((item, i) => renderItemRow(item, i))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="space-y-2">
      {items.length === 0 ? (
        <p className="text-sm text-gray-400 italic px-3">
          No items yet. Upload a document and it will be classified automatically.
        </p>
      ) : (
        <>
          {renderSection("Needs Review", itemsByType.needs_review, "bg-yellow-50")}
          {renderSection("Income", itemsByType.income, "bg-green-50")}
          {renderSection("Deductions", itemsByType.deduction, "bg-blue-50")}
          {renderSection("Out of Scope", itemsByType.out_of_scope, "bg-gray-50")}
        </>
      )}
    </div>
  );
}
