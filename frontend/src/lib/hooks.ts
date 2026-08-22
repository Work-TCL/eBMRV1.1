"use client";

import { useEffect, useState } from "react";
import { api, type Me, type Site } from "./api";

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
