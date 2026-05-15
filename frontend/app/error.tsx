"use client";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center space-y-4 p-8">
        <div className="text-6xl font-bold text-red-200">500</div>
        <h1 className="text-xl font-semibold text-gray-700">Something went wrong</h1>
        <p className="text-sm text-gray-500 max-w-sm">
          An unexpected error occurred. Please try again.
        </p>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={reset}
            className="px-4 py-2 text-sm font-medium text-white bg-ato-blue rounded hover:bg-blue-700"
          >
            Try again
          </button>
          <a
            href="/"
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50"
          >
            Back to home
          </a>
        </div>
      </div>
    </div>
  );
}
