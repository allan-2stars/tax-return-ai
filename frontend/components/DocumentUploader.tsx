"use client";

import { useState, useRef, useCallback } from "react";
import { BatchProgress } from "./BatchProgress";

interface BatchItem {
  jobId: string;
  filename: string;
}

export function DocumentUploader({
  sessionId,
  financialYear,
  onUploaded,
}: {
  sessionId: string;
  financialYear: string;
  onUploaded: () => void;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [category, setCategory] = useState("receipt");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [batchItems, setBatchItems] = useState<BatchItem[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

  const handleFilesSelected = useCallback((selectedFiles: FileList | File[]) => {
    const validFiles: File[] = [];
    const files = Array.from(selectedFiles);
    for (const f of files) {
      const ext = f.name.split(".").pop()?.toLowerCase();
      if (["pdf", "png", "jpg", "jpeg", "tiff", "tif"].includes(ext || "")) {
        validFiles.push(f);
      }
    }
    setFiles(validFiles);
    setError(null);
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) return;

    setUploading(true);
    setError(null);
    setBatchItems([]);

    try {
      const fd = new FormData();
      fd.append("session_id", sessionId);
      fd.append("category", category);
      fd.append("financial_year", financialYear);
      for (const f of files) {
        fd.append("files", f);
      }

      const res = await fetch(`${apiUrl}/api/documents/upload/batch`, {
        method: "POST",
        body: fd,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Upload failed: ${text}`);
      }

      const data = await res.json();

      if (data.documents && data.documents.length > 0) {
        setBatchItems(
          data.documents.map((d: { job_id: string; filename: string }) => ({
            jobId: d.job_id,
            filename: d.filename,
          }))
        );
        setFiles([]);
        if (inputRef.current) inputRef.current.value = "";
      } else {
        setError("No files were accepted. Check file types and sizes.");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleAllComplete = () => {
    onUploaded();
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleFilesSelected(e.dataTransfer.files);
    }
  };

  const totalSize = files.reduce((sum, f) => sum + f.size, 0);

  return (
    <div className="space-y-3">
      <form onSubmit={handleUpload} className="space-y-3">
        <div className="flex items-start gap-3 flex-wrap">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`relative flex-1 min-w-[200px] border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
              isDragOver
                ? "border-ato-blue bg-blue-50"
                : "border-gray-300 hover:border-gray-400 bg-white"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              name="files"
              multiple
              accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
              onChange={(e) => {
                if (e.target.files) handleFilesSelected(e.target.files);
              }}
              className="hidden"
            />
            <p className="text-sm text-gray-500">
              {files.length > 0
                ? `${files.length} file(s) selected (${(totalSize / 1024 / 1024).toFixed(1)} MB)`
                : "Drop files here or click to browse"}
            </p>
            <p className="text-xs text-gray-400 mt-1">PDF, PNG, JPG, TIFF — up to 20MB each</p>
          </div>
          <select
            name="category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="text-sm border border-gray-300 rounded px-2 py-1.5"
          >
            <option value="receipt">Receipt</option>
            <option value="invoice">Invoice</option>
            <option value="income_statement">Income Statement</option>
            <option value="bank_statement">Bank Statement</option>
            <option value="utility_bill">Utility Bill</option>
            <option value="bas_statement">BAS Statement</option>
            <option value="other">Other</option>
          </select>
          <button
            type="submit"
            disabled={files.length === 0 || uploading}
            className="px-4 py-1.5 text-sm font-medium text-white bg-ato-green rounded hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {uploading ? "Uploading..." : `Upload ${files.length > 0 ? `(${files.length})` : ""}`}
          </button>
        </div>
        {files.length > 0 && !uploading && (
          <div className="text-xs text-gray-500 space-y-1">
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-2">
                <span>{i + 1}.</span>
                <span className="truncate max-w-[300px]">{f.name}</span>
                <span>({(f.size / 1024).toFixed(1)} KB)</span>
              </div>
            ))}
          </div>
        )}
        {error && (
          <p className="text-sm text-ato-red bg-red-50 px-3 py-2 rounded">{error}</p>
        )}
      </form>

      {batchItems.length > 0 && (
        <BatchProgress items={batchItems} />
      )}

      {batchItems.length > 0 && (
        <button
          onClick={handleAllComplete}
          className="text-xs text-ato-blue hover:underline"
        >
          Refresh item list
        </button>
      )}
    </div>
  );
}
