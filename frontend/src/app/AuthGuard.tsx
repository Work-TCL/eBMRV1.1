"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/api";
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

  if (!ready && !isLoginRoute) return null;
  if (isLoginRoute) return <>{children}</>;
  return <AppShell>{children}</AppShell>;
}
