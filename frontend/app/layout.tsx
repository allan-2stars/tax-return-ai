import type { Metadata } from "next";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import "./globals.css";

export const metadata: Metadata = {
  title: "tax-return-ai — Tax Organiser",
  description:
    "Australian individual tax-ready data generator. Review and organise your tax documents before lodgement.",
};

/**
 * Root layout — wraps every page.
 * The DisclaimerBanner must be visible on every page, never conditional.
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <nav className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-4">
          <a
            href="/"
            className="text-lg font-semibold text-ato-blue hover:underline"
          >
            tax-return-ai
          </a>
          <span className="text-xs text-gray-400">|</span>
          <span className="text-xs text-gray-500">
            Draft — for review only. Not a tax return.
          </span>
        </nav>
        <main className="max-w-5xl mx-auto px-4 py-6">
          <DisclaimerBanner />
          {children}
        </main>
        <footer className="text-center text-xs text-gray-400 py-4 border-t border-gray-200">
          tax-return-ai v0.1.0 — This tool does not provide tax advice or lodge
          returns. Always consult a registered tax agent.
        </footer>
      </body>
    </html>
  );
}
