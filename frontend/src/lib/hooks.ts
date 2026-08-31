"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, isAdminAnywhere, type Me, type Site } from "./api";

export function useSites() {
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<Site[]>("/sites")
      .then(setSites)
      .finally(() => setLoading(false));
  }, []);

  return { sites, loading };
}

export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

export function useMe() {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<Me>("/auth/me")
      .then(setMe)
      .catch(() => setMe(null))
      .finally(() => setLoading(false));
  }, []);

  return { me, loading };
}

/** Shared gate for every /admin/* page: redirect away unless the signed-in user holds Admin at any
 * site. Each admin page calls this once instead of duplicating the same effect. */
export function useRequireAdmin(redirectTo = "/products") {
  const { me, loading } = useMe();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAdminAnywhere(me)) {
      router.replace(redirectTo);
    }
  }, [me, loading, router, redirectTo]);

  return { me, loading, isAdmin: isAdminAnywhere(me) };
}

/** The site to scope site-required reads to (equipment/risk/metrics dashboards, QMS lists).
 *
 * Phase 1 deployments are single-site — `assert_single_organization` in app/core/db.py enforces one
 * organization, and every existing page already reaches for `sites[0]`. This centralises that
 * assumption in one place so a future site switcher has a single call site to replace, rather than
 * being scattered across every dashboard. */
export function useSiteId(): { siteId: string | null; loading: boolean } {
  const { sites, loading } = useSites();
  return { siteId: sites[0]?.id ?? null, loading };
}

/** GET one resource with loading/error state and an explicit refetch.
 *
 * Detail pages all need the same three-state shape after an action commits, and each was otherwise
 * about to hand-roll it. Pass `path: null` to hold off until a dependency (a site id, a selected row)
 * is known — the hook stays in its loading state rather than firing a request at a bad URL. */
export function useApiResource<T>(path: string | null): {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
} {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [token, setToken] = useState(0);

  useEffect(() => {
    if (path === null) return;
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    api
      .get<T>(path)
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to load");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [path, token]);

  return { data, loading, error, reload: () => setToken((n) => n + 1) };
}
