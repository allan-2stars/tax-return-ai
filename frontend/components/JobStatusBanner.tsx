"use client";

import { useEffect, useState, useRef } from "react";
import { api, type JobStatus } from "@/lib/api";

export function JobStatusBanner({
  jobId,
  onComplete,
}: {
  jobId: string;
  onComplete?: () => void;
}) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let attempts = 0;
    const maxAttempts = 60;

    const poll = async () => {
      attempts++;
      try {
        const s = await api.getJobStatus(jobId);
        setStatus(s);
        setError(null);

        if (s.status === "succeeded" || s.status === "failed") {
          if (pollingRef.current) clearInterval(pollingRef.current);
          pollingRef.current = null;
          if (s.status === "succeeded" && onComplete) {
            onComplete();
          }
        } else if (attempts >= maxAttempts) {
          if (pollingRef.current) clearInterval(pollingRef.current);
          pollingRef.current = null;
          setError("Job timed out");
        }
      } catch (err) {
        if (attempts >= maxAttempts) {
          if (pollingRef.current) clearInterval(pollingRef.current);
          pollingRef.current = null;
          setError("Job polling failed");
        }
      }
    };

    poll();
    pollingRef.current = setInterval(poll, 3000);

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [jobId, onComplete]);

  if (dismissed) return null;

  if (!status) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 px-3 py-2 rounded animate-pulse">
        <div className="w-2 h-2 rounded-full bg-gray-400" />
        <span>Processing upload...</span>
      </div>
    );
  }

  const isRunning = status.status === "running" || status.status === "queued";
  const isSucceeded = status.status === "succeeded";
  const isFailed = status.status === "failed";
  const progress = status.progress ?? (status.status === "queued" ? 0 : status.status === "running" ? 0.5 : 1);

  const barColor = isSucceeded
    ? "bg-green-500"
    : isFailed
      ? "bg-red-500"
      : "bg-ato-blue";

  // Succeeded: green success banner with dismiss
  if (isSucceeded) {
    return (
      <div className="flex items-center justify-between gap-2 text-xs bg-green-50 border border-green-200 text-green-700 rounded px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="text-green-600 font-bold">✓</span>
          <span>Upload complete — document classified</span>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-green-500 hover:text-green-700 font-medium"
        >
          Dismiss
        </button>
      </div>
    );
  }

  // Failed: red error banner
  if (isFailed) {
    return (
      <div className="flex items-center justify-between gap-2 text-xs bg-red-50 border border-red-200 text-red-700 rounded px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="text-red-600 font-bold">✗</span>
          <span>Upload failed: {status.error_message || "Unknown error"}</span>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-red-500 hover:text-red-700 font-medium"
        >
          Dismiss
        </button>
      </div>
    );
  }

  // Running / queued: progress bar
  return (
    <div className="text-xs rounded px-3 py-2 border bg-gray-50 border-gray-200 text-gray-600">
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="font-medium capitalize">{status.job_type}</span>
        <span className="text-xs">{status.progress_message || status.status}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${Math.round(progress * 100)}%` }}
        />
      </div>
    </div>
  );
}
