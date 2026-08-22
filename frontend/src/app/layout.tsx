import type { Metadata } from "next";
import "./globals.css";
import AuthGuard from "./AuthGuard";

export const metadata: Metadata = {
  title: "eBMR",
  description: "eBMR batch record kernel — Phase 1",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <AuthGuard>{children}</AuthGuard>
      </body>
    </html>
  );
}
