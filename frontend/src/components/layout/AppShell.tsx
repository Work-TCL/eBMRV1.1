"use client";

import { useState, type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppShell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar open={sidebarOpen} />
      <div className="main-col">
        <Topbar onToggleSidebar={() => setSidebarOpen((v) => !v)} />
        <main id="main" className="content">
          {children}
        </main>
      </div>
    </div>
  );
}
