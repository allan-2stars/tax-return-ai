import type { Metadata } from "next";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tax Return AI",
  description:
    "Local-first Australian tax evidence review and review-pack workflow.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-slate-200 bg-white/90 px-6 py-4 backdrop-blur">
          <div className="mx-auto flex w-full max-w-7xl items-center justify-between">
            <div>
              <a href="/" className="text-base font-semibold tracking-tight text-slate-900">
                Tax Return AI
              </a>
              <p className="text-xs text-slate-500">Local-first tax evidence review</p>
            </div>
            <p className="text-xs text-slate-400">Draft workflow foundation</p>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl px-6 py-6">
          <div className="mb-4">
            <DisclaimerBanner />
          </div>
          {children}
        </main>
      </body>
    </html>
  );
}
