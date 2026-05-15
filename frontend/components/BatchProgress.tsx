"use client";

import { useEffect, useState, useRef } from "react";
import { api, type JobStatus } from "@/lib/api";

function JobProgressItem({
  jobId,
  filename,
  onComplete,
}: {
  jobId: string;
  filename: string;
  onComplete: () => void;
}) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let attempts = 0;
    const maxAttempts = 60;

    const poll = async () => {
      attempts++;
      try {
        const s = await api.getJobStatus(jobId);
        setStatus(s);
        if (s.status === "succeeded" || s.status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          intervalRef.current = null;
          onComplete();
        } else if (attempts >= maxAttempts) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } catch {
        if (attempts >= maxAttempts) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId, onComplete]);

  const progress = status?.progress ?? (status?.status === "queued" ? 0 : 0.5);
  const isDone = status?.status === "succeeded" || status?.status === "failed";
  const barColor = status?.status === "succeeded" ? "bg-green-500" : status?.status === "failed" ? "bg-red-500" : "bg-ato-blue";

  const fileNameShort = filename.length > 30 ? filename.slice(0, 27) + "..." : filename;

  return (
    <div className="flex items-center gap-3 text-xs text-gray-600 px-3 py-2 bg-white border border-gray-200 rounded">
      <span className="w-4 text-center">
        {status?.status === "succeeded" ? "✓" : status?.status === "failed" ? "✗" : "⋯"}
      </span>
      <span className="truncate max-w-[150px] font-medium" title={filename}>
        {fileNameShort}
      </span>
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full max-w-[120px]">
        <div className={`h-1.5 rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${Math.round(progress * 100)}%` }} />
      </div>
      <span className="text-gray-400 min-w-[60px] text-right">
        {isDone ? (status?.status === "succeeded" ? "Done" : "Failed") : status?.progress_message || status?.status || "Queued"}
      </span>
    </div>
  );
}

export function BatchProgress({
  items,
}: {
  items: Array<{ jobId: string; filename: string }>;
}) {
  const [completed, setCompleted] = useState(0);

  const handleComplete = () => {
    setCompleted((c) => c + 1);
  };

  if (items.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span className="font-medium">Uploading {items.length} file(s)</span>
        <span>{completed}/{items.length} complete</span>
      </div>
      <div className="space-y-1">
        {items.map((item) => (
          <JobProgressItem
            key={item.jobId}
            jobId={item.jobId}
            filename={item.filename}
            onComplete={handleComplete}
          />
        ))}
      </div>
      {completed === items.length && completed > 0 && (
        <p className="text-xs text-green-600 font-medium">✓ All files processed</p>
      )}
    </div>
  );
}
