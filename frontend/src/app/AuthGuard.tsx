"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { isLoggedIn, isAdminAnywhere, SESSION_EXPIRED_EVENT } from "@/lib/api";
import { useMe, useOnboardingStatus } from "@/lib/hooks";
import { AppShell } from "@/components/layout/AppShell";

/** Sends a signed-in Admin to the onboarding wizard until all four steps are done or the admin has
 * explicitly skipped it (client gap-analysis follow-up, 2026-10-06) -- mounted only once AuthGuard has
 * already confirmed the user is logged in and off the login route, so `useMe()`/`useOnboardingStatus()`
 * never fire an extra request on the login page itself. */
function OnboardingGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { me, loading: meLoading } = useMe();
  const { status, loading: statusLoading } = useOnboardingStatus();

  useEffect(() => {
    // Every "Set up"/"Review" link the wizard and the home-page checklist render points at
    // /admin/company, /admin/sites, /admin/users or /admin/roles(/[id]) -- exempting the whole /admin
    // subtree (not just /onboarding itself) is what actually lets those links work. Without it, this
    // same redirect fired again the instant the admin landed on /admin/company, bouncing them straight
    // back to /onboarding before they could do anything -- the wizard could send you to a step but
    // never let you complete it.
    if (meLoading || statusLoading || pathname === "/onboarding" || pathname.startsWith("/admin")) return;
    if (isAdminAnywhere(me) && status && !status.all_done && !status.dismissed_at) {
      router.replace("/onboarding");
    }
  }, [me, meLoading, status, statusLoading, pathname, router]);

  return <>{children}</>;
}

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  // /accept-invite (client gap-analysis Phase 1, 2026-10-05) is reached from an emailed link by someone
  // who, by definition, has no session yet -- same public-route treatment as /login.
  const isLoginRoute = pathname === "/login" || pathname === "/accept-invite";
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
  return (
    <OnboardingGate>
      <AppShell>{children}</AppShell>
    </OnboardingGate>
  );
}
