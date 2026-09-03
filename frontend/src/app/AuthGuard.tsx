"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { isLoggedIn, SESSION_EXPIRED_EVENT } from "@/lib/api";
import { AppShell } from "@/components/layout/AppShell";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const isLoginRoute = pathname === "/login";
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Reading localStorage is a browser-only external system unknowable at server-render time —
    // this is exactly what an effect is for, so the "no setState in effect" rule is suppressed
    // deliberately for this one synchronization, rather than avoided with a workaround.
    if (!isLoginRoute && !isLoggedIn()) {
      router.replace("/login");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReady(true);
  }, [isLoginRoute, router]);

  useEffect(() => {
    // The token can expire (or be revoked) at any moment while the user is sitting on a page, not just
    // on navigation — `api.ts::request()` has no router of its own (it's called from outside any
    // component tree), so it clears the token and fires this event; this is the one place that reacts
    // by actually sending the user to /login, same as Sidebar's own "Sign out" button. Without this, a
    // page whose data calls start 401ing just sits there showing stale content and error banners —
    // never logged out, never told why — which is the bug this fixes.
    function onSessionExpired() {
      if (!isLoginRoute) router.replace("/login");
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
  }, [isLoginRoute, router]);

  if (!ready && !isLoginRoute) return null;
  if (isLoginRoute) return <>{children}</>;
  return <AppShell>{children}</AppShell>;
}
