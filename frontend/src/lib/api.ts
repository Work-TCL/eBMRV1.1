// The backend always runs on the same host as this frontend, on port 8010. Resolving this from
// window.location at request time (rather than a build-time constant) means the app works whether
// it's reached via localhost, a LAN IP, a public IP, or a hostname — no rebuild needed per environment.
// NEXT_PUBLIC_GXP_API_BASE can still override this explicitly (e.g. for a split-host deployment).
function apiBase(): string {
  if (process.env.NEXT_PUBLIC_GXP_API_BASE) return process.env.NEXT_PUBLIC_GXP_API_BASE;
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8010`;
  }
  return "http://localhost:8010";
}

// crypto.randomUUID() is gated to "secure contexts" (HTTPS, or exactly `localhost`) — it throws
// "crypto.randomUUID is not a function" over plain HTTP via an IP or hostname, which is exactly how
// this app gets accessed in dev/demo. crypto.getRandomValues() has no such restriction, so build the
// UUID from that instead. The backend only requires idempotency_key to be a non-empty string, but a
// real RFC 4122 v4 shape keeps it consistent with every other id in the system.
export function newIdempotencyKey(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  status: number;

  constructor(status: number, code: string, message: string, details: Record<string, unknown>) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("gxp_token");
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem("gxp_token", token);
  else window.localStorage.removeItem("gxp_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${apiBase()}${path}`, { ...options, headers });
  if (!res.ok) {
    let body: { code?: string; message?: string; details?: Record<string, unknown> } = {};
    try {
      body = await res.json();
    } catch {
      // non-JSON error body
    }
    throw new ApiError(
      res.status,
      body.code ?? "UNKNOWN_ERROR",
      body.message ?? res.statusText,
      body.details ?? {}
    );
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
};

// --- Server-side list pagination (products/recipes/batches all share this envelope) ------------

export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ListQuery {
  page: number;
  page_size: number;
  q: string;
  sort_by: string | null;
  sort_dir: "asc" | "desc";
}

/** For populating a <select> with "all" rows — fine while row counts are small (Phase 1). 100 is the
 * backend's own hard cap (app/core/pagination.py page_size Query(..., le=100)) — once any resource can
 * realistically exceed that, this dropdown should become a searchable combobox hitting the paginated
 * endpoint directly instead of trying to raise the cap. */
export async function listAll<T>(path: string): Promise<T[]> {
  const result = await pagedFetcher<T>(path)({ page: 1, page_size: 100, q: "", sort_by: null, sort_dir: "asc" });
  return result.items;
}

/** `extraParams` is re-read on every call, so a caller can pass a ref/getter for filters (e.g. status)
 * that change without needing a new DataTable `fetchPage` identity each time. */
export function pagedFetcher<T>(path: string, extraParams?: () => Record<string, string>) {
  return (query: ListQuery) => {
    const search = new URLSearchParams({
      page: String(query.page),
      page_size: String(query.page_size),
      sort_dir: query.sort_dir,
    });
    if (query.q) search.set("q", query.q);
    if (query.sort_by) search.set("sort_by", query.sort_by);
    for (const [key, value] of Object.entries(extraParams?.() ?? {})) {
      if (value) search.set(key, value);
    }
    return api.get<Paged<T>>(`${path}?${search.toString()}`);
  };
}

export async function login(username: string, password: string): Promise<string> {
  const res = await fetch(`${apiBase()}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username, password }),
  });
  if (!res.ok) {
    throw new ApiError(res.status, "UNAUTHORIZED", "Invalid username or password", {});
  }
  const data = (await res.json()) as { access_token: string };
  setToken(data.access_token);
  return data.access_token;
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

export function logout() {
  setToken(null);
}

// --- Domain types -----------------------------------------------------

export interface MutationReceipt {
  command_id: string;
  aggregate_id: string;
  resulting_version: number;
  audit_event_id: string;
  signature_id: string | null;
  correlation_id: string;
}

export interface Product {
  id: string;
  site_id: string;
  code: string;
  name: string;
  status: string;
  version: number;
}

export interface RecipeStep {
  id?: string;
  step_number: number;
  name: string;
  instructions?: string | null;
  requires_signature: boolean;
  signature_meaning?: string | null;
}

export interface RecipeSummary {
  id: string;
  product_id: string;
  product_code: string;
  product_name: string;
  version: number;
  status: string;
}

export interface RecipeDetail extends RecipeSummary {
  steps: RecipeStep[];
}

export interface BatchSummary {
  id: string;
  batch_number: string;
  status: string;
  product_id: string;
  product_code: string;
  product_name: string;
  target_quantity: string;
  uom: string;
  version: number;
}


export interface BatchStepDetail {
  batch_step_id: string;
  recipe_step_id: string;
  step_number: number;
  name: string;
  status: string;
  requires_signature: boolean;
  signature_meaning: string | null;
  data: Record<string, unknown> | null;
}

export interface BatchDetail extends BatchSummary {
  site_id: string;
  recipe_id: string;
  target_quantity: string;
  uom: string;
  steps: BatchStepDetail[];
}

export interface Material {
  id: string;
  site_id: string;
  code: string;
  name: string;
  uom: string;
  status: string;
  version: number;
}

export interface MaterialLot {
  id: string;
  material_id: string;
  material_code: string;
  material_name: string;
  internal_lot: string;
  supplier_lot: string | null;
  manufacturer_lot: string | null;
  received_quantity: string;
  available_quantity: string;
  uom: string;
  status: string;
  expiry_date: string | null;
  retest_date: string | null;
  version: number;
}

export interface MaterialIssueRecord {
  id: string;
  material_lot_id: string;
  internal_lot: string;
  material_code: string;
  material_name: string;
  batch_step_id: string | null;
  quantity: string;
  uom: string;
  issued_at: string;
}

export interface Site {
  id: string;
  code: string;
  name: string;
}

export interface Me {
  user_id: string;
  username: string;
  roles_by_site: Record<string, string[]>;
}
