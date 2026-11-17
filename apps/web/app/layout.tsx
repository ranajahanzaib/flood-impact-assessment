import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Flood Impact Assessment | Evidence Platform",
  description: "Multi-Sensor Geospatial Flood Impact Evidence Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#090d16] text-[#e2e8f0] font-sans antialiased min-h-screen flex flex-col selection:bg-blue-600 selection:text-white">
        <header className="border-b border-[#1e293b] bg-[#0c1220]/90 backdrop-blur sticky top-0 z-50 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <Link href="/" className="flex items-center space-x-3 group">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-sky-700 flex items-center justify-center font-bold text-white shadow-md shadow-blue-500/20">
                F
              </div>
              <div>
                <span className="font-semibold tracking-tight text-white text-base">
                  Flood Impact Assessment
                </span>
                <span className="text-[10px] text-sky-400 block tracking-wider uppercase font-mono">
                  Evidence Platform
                </span>
              </div>
            </Link>

            <nav className="flex items-center space-x-1 text-sm font-medium">
              <Link
                href="/"
                className="px-3 py-1.5 rounded-md hover:bg-[#1e293b] text-slate-300 hover:text-white transition-colors"
              >
                Overview
              </Link>
              <Link
                href="/events"
                className="px-3 py-1.5 rounded-md hover:bg-[#1e293b] text-slate-300 hover:text-white transition-colors"
              >
                Flood Events
              </Link>
              <Link
                href="/datasets"
                className="px-3 py-1.5 rounded-md hover:bg-[#1e293b] text-slate-300 hover:text-white transition-colors"
              >
                Datasets
              </Link>
              <Link
                href="/models"
                className="px-3 py-1.5 rounded-md hover:bg-[#1e293b] text-slate-300 hover:text-white transition-colors"
              >
                Models
              </Link>
              <Link
                href="/reports"
                className="px-3 py-1.5 rounded-md hover:bg-[#1e293b] text-slate-300 hover:text-white transition-colors"
              >
                Reports
              </Link>
            </nav>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-xs font-mono text-slate-400 bg-[#161f30] px-3 py-1.5 rounded border border-[#233149]">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>API ONLINE</span>
            </div>
            <Link
              href="/events/new"
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-xs font-medium tracking-wide transition-colors shadow-sm"
            >
              + New Analysis
            </Link>
          </div>
        </header>

        <main className="flex-1 flex flex-col">{children}</main>
      </body>
    </html>
  );
}
