export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center space-y-4 p-8">
        <div className="text-6xl font-bold text-gray-200">404</div>
        <h1 className="text-xl font-semibold text-gray-700">Page not found</h1>
        <p className="text-sm text-gray-500 max-w-sm">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <a
          href="/"
          className="inline-block px-4 py-2 text-sm font-medium text-white bg-ato-blue rounded hover:bg-blue-700"
        >
          Back to home
        </a>
      </div>
    </div>
  );
}
