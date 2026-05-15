/**
 * API client — ALL fetch() calls to the FastAPI backend live here.
 * Never call fetch() directly from components or pages.
 */
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  // TODO: add typed methods for sessions, documents, analysis, review, export
};
