"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function ExportButton({ sessionId }: { sessionId: string }) {
  const [exporting, setExporting] = useState(false);
  const [exportData, setExportData] = useState<string | null>(null);

  const handleExport = async () => {
    setExporting(true);
    try {
      const pkg = await api.exportSession(sessionId);
      const json = JSON.stringify(pkg, null, 2);
      setExportData(json);

      // Trigger download
      const blob = new Blob([json], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tax-export-${sessionId.slice(0, 8)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div>
      <button
        onClick={handleExport}
        disabled={exporting}
        className="px-4 py-2 text-sm font-medium text-white bg-ato-blue rounded hover:bg-blue-700 disabled:opacity-40"
      >
        {exporting ? "Exporting..." : "Export Review Package"}
      </button>
      {exportData && (
        <details className="mt-3">
          <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
            Preview export JSON
          </summary>
          <pre className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded text-xs overflow-auto max-h-96">
            {exportData}
          </pre>
        </details>
      )}
    </div>
  );
}
