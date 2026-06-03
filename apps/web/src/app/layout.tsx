import type { Metadata } from "next";

import { Providers } from "@/lib/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "SFQA Intelligence Platform",
  description: "Salesforce QA Requirement Intelligence Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
