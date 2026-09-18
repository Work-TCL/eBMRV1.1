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

/** Dispatched on `window` the moment any API call comes back 401 (expired/invalid/revoked token) —
 * `AuthGuard` listens for this to send the user back to /login, the one place in this module tree that
 * holds a router. See its usage in `request()` below. */
export const SESSION_EXPIRED_EVENT = "gxp:session-expired";

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
    // A 401 here always means the bearer token is missing/expired/revoked (get_current_actor's only
    // failure mode — see app/core/security.py) rather than a business rejection, so it's handled once,
    // centrally, instead of leaving every page to notice its own API calls started failing and show a
    // stale panel with error banners. This module has no router (it's called from outside any component
    // tree), so it clears the token and raises a DOM event; AuthGuard — which does hold a router, the
    // same way Sidebar's own "Sign out" button does — is what actually navigates to /login.
    if (res.status === 401 && typeof window !== "undefined" && window.location.pathname !== "/login") {
      setToken(null);
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
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

/** `GET /evidence/v1/{evidence_id}/download` returns raw bytes with a `Content-Disposition` header, not
 * JSON — `request()` above always parses a JSON body, so this is a separate helper rather than another
 * `api.*` method. Auth still needs the bearer header (this endpoint isn't cookie-authenticated), so a
 * plain `<a href>` can't be used directly — fetch with the token, then hand the browser a blob URL to
 * save under the server's own suggested filename. */
export async function downloadEvidence(evidenceId: string, purpose = "inspection"): Promise<void> {
  const token = getToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(
    `${apiBase()}/evidence/v1/${encodeURIComponent(evidenceId)}/download?purpose=${encodeURIComponent(purpose)}`,
    { headers }
  );
  if (!res.ok) {
    let body: { code?: string; message?: string; details?: Record<string, unknown> } = {};
    try {
      body = await res.json();
    } catch {
      // non-JSON error body
    }
    throw new ApiError(res.status, body.code ?? "UNKNOWN_ERROR", body.message ?? res.statusText, body.details ?? {});
  }
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const filenameMatch = /filename="?([^";]+)"?/.exec(disposition);
  const filename = filenameMatch?.[1] ?? evidenceId;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  try {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "DELETE", body: body ? JSON.stringify(body) : undefined }),
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
 * endpoint directly instead of trying to raise the cap.
 *
 * `extraQuery` values are always set verbatim, including `""` — unlike `pagedFetcher`'s `extraParams`,
 * which treats a blank value as "not filtering". That distinction matters for endpoints like DDCP's
 * `GET /profiles`, where an explicit `state=` (empty) overrides a non-empty server-side default and an
 * omitted `state` falls back to it — so a caller that means "no filter" must be able to send the empty
 * string rather than have it silently dropped. */
export async function listAll<T>(path: string, extraQuery?: Record<string, string>): Promise<T[]> {
  const search = new URLSearchParams({ page: "1", page_size: "100", sort_dir: "asc" });
  for (const [k, v] of Object.entries(extraQuery ?? {})) search.set(k, v);
  const result = await api.get<Paged<T>>(`${path}?${search.toString()}`);
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

/** Adapts a plain (non-paginated) list endpoint to DataTable's page/sort/search contract, for the
 * handful of listing endpoints (batches, product/recipe families) that don't carry the server-side
 * `Paged<T>` envelope yet (Phase 1, small row counts — same ceiling `listAll` documents above).
 * `fetchAll` is called on every page/sort/search/reloadToken change, same as `pagedFetcher` calling
 * the network each time — so a caller wanting to avoid re-fetching on every keystroke should have
 * `fetchAll` read from an already-loaded source instead of hitting the API directly. */
export function clientPagedFetcher<T>(
  fetchAll: () => Promise<T[]>,
  opts: {
    searchText: (row: T) => string;
    sortValue?: (row: T, sortBy: string) => string | number | null;
  }
) {
  return async (query: ListQuery): Promise<Paged<T>> => {
    let rows = await fetchAll();
    if (query.q) {
      const q = query.q.toLowerCase();
      rows = rows.filter((row) => opts.searchText(row).toLowerCase().includes(q));
    }
    if (query.sort_by) {
      const sortBy = query.sort_by;
      const getValue = opts.sortValue ?? ((row: T) => (row as Record<string, unknown>)[sortBy] as string | number | null);
      const dir = query.sort_dir === "asc" ? 1 : -1;
      rows = [...rows].sort((a, b) => {
        const av = getValue(a, sortBy);
        const bv = getValue(b, sortBy);
        if (av == null && bv == null) return 0;
        if (av == null) return -1;
        if (bv == null) return 1;
        if (av < bv) return -dir;
        if (av > bv) return dir;
        return 0;
      });
    }
    const total = rows.length;
    const total_pages = Math.max(1, Math.ceil(total / query.page_size));
    const page = Math.min(Math.max(1, query.page), total_pages);
    const start = (page - 1) * query.page_size;
    return { items: rows.slice(start, start + query.page_size), total, page, page_size: query.page_size, total_pages };
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

/** Revokes the session server-side (`POST /auth/logout` — `iam/router.py`'s `logout()` builds the
 * `RevokeSessionCommand` itself from the token's own `session_id`, no body needed) before clearing the
 * local token, so a "logged out" session doesn't stay ACTIVE server-side until natural expiry. The local
 * token is always cleared, even if the network call fails, so the user is never stuck unable to log out. */
export async function logout(): Promise<void> {
  try {
    await api.post("/auth/logout");
  } catch {
    // Best-effort server-side revoke — clear the local token regardless (e.g. token already expired,
    // or this token was never session-tracked, per that endpoint's own "nothing to log out" case).
  } finally {
    setToken(null);
  }
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

interface GxpBatchListRow {
  batch_id: string;
  batch_number: string;
  state: string;
  product_version_id: string;
  product_code: string | null;
  product_name: string | null;
  target_qty: string;
  target_uom: string;
  version: number;
}

/** Real batch picker data — SG-149/SG-173 cutover (2026-09-08, project-owner-directed): every batch now
 * lives in `ebmr.gxp_batch` (`GET /batches/v1`), not the retired legacy `ebmr.batches` table this
 * function used to read via `listAll<BatchSummary>("/batches")`. Reshaped into `BatchSummary`'s existing
 * field names so every existing picker (dispensing/packaging/inventory/`useEntityOptions`) needed no JSX
 * changes, only this one fetch swapped in. `/batches/v1` is scoped by site (unlike the old endpoint), so
 * this takes the caller's current site id rather than being a bare path constant. */
export async function listBatchesForSite(siteId: string): Promise<BatchSummary[]> {
  const result = await api.get<{ batches: GxpBatchListRow[] }>(`/batches/v1?site_id=${siteId}`);
  return result.batches.map((b) => ({
    id: b.batch_id,
    batch_number: b.batch_number,
    status: b.state,
    product_id: b.product_version_id,
    product_code: b.product_code ?? "",
    product_name: b.product_name ?? "",
    target_quantity: b.target_qty,
    uom: b.target_uom,
    version: b.version,
  }));
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
  supplier_id: string | null;
  supplier_lot: string | null;
  manufacturer_lot: string | null;
  received_quantity: string;
  available_quantity: string;
  uom: string;
  status: string;
  received_at: string | null;
  released_at: string | null;
  expiry_date: string | null;
  retest_date: string | null;
  version: number;
}

export interface MaterialContainer {
  id: string;
  container_code: string;
  current_quantity: string;
  uom: string;
  container_status: string;
  quality_status_override: string | null;
}

export interface WarehouseLocation {
  id: string;
  warehouse_code: string;
  location_code: string;
  zone_type: string;
  status: string;
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
  // The user's actual resolved permission codes per site -- computed live on the backend from
  // whatever roles the user currently holds and whatever those roles are currently granted (GET
  // /auth/me, see app/modules/iam/service.py::get_permission_codes). Every UI gate in this file should
  // check THIS, not roles_by_site: role names are ordinary user-editable data (a customer can rename,
  // delete, or re-permission any role except Admin at any time via /admin/roles), so a gate hardcoded
  // against a role name silently goes stale the moment someone edits that role. A gate built on a
  // permission code can't drift the same way, because it's the same vocabulary evaluate_policy() itself
  // checks server-side.
  permissions_by_site: Record<string, string[]>;
}

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  status: string;
  roles: string[];
}

export interface Role {
  id: string;
  name: string;
  description: string | null;
}

export interface Organization {
  id: string;
  name: string;
}

export interface Permission {
  id: string;
  code: string;
  action: string;
  resource_type: string;
  description: string | null;
}

/** True if `me` holds the Admin role at any site — the gate for /admin and its nav entry.
 *
 * "Admin" is the one role name this file is still allowed to hardcode. Every other role in this system
 * is data a customer creates, renames, re-permissions or deletes freely via /admin/roles; Admin is the
 * platform's own fixed, non-editable, non-deletable break-glass superuser (enforced server-side in
 * app/modules/iam/commands.py::update_role/delete_role/set_role_permissions), so a literal check against
 * its name can never go stale the way a check against any other role name could. */
export function isAdminAnywhere(me: Me | null): boolean {
  if (!me) return false;
  return Object.values(me.roles_by_site).some((roles) => roles.includes("Admin"));
}

/** True if `me` holds `code` at any site. The primitive every capability helper below should be built
 * on — see the `permissions_by_site` doc comment on `Me` above for why. */
export function hasPermission(me: Me | null, code: string): boolean {
  if (!me) return false;
  return Object.values(me.permissions_by_site).some((perms) => perms.includes(code));
}

/** True if `me` holds any of `codes` at any site. For the handful of gates that legitimately span
 * several independent permission codes (e.g. a console bundling multiple sub-features each with their
 * own grant) — every code in the list should still be a real permission code, never a role name. */
export function hasAnyPermission(me: Me | null, codes: readonly string[]): boolean {
  if (!me) return false;
  return Object.values(me.permissions_by_site).some((perms) => perms.some((p) => codes.includes(p)));
}

export const canReviewAudit = (me: Me | null) => hasPermission(me, "audit.review");
export const canReviewVault = (me: Me | null) => hasPermission(me, "vault.review");
export const canCorrectVault = (me: Me | null) => hasPermission(me, "vault.correct");
// evidence.upload/.download share one grant (Document 72) — the /platform "Evidence operations"
// (stage/finalize) section.
export const canOperateEvidence = (me: Me | null) => hasPermission(me, "evidence.upload");

// The /security console bundles several genuinely independent permission domains (Documents 61-68) --
// threat modelling, risk acceptance, IdP/session admin, secrets/certs, incident response, break-glass
// access -- each held by a different one of the five security roles, with no single shared code. Gating
// the console's visibility is therefore an OR across one representative "entry" code per domain, same
// as any dashboard bundling independently-permissioned widgets.
const SECURITY_ENTRY_CODES = [
  "security_threat_model.create", "security_control_matrix.view", "security_exception.view",
  "identity_provider.create", "secret.create", "security_incident.open", "vulnerability.register",
  "privileged_access.request", "privileged_access.view", "privileged_session.open_support",
];
export const canOperateSecurity = (me: Me | null) => hasAnyPermission(me, SECURITY_ENTRY_CODES);

// material_lot.release / .reject (Document 19 RCV-FR-026/027) -- distinct from the legacy
// material_lot.disposition path the /material-lots page's "Disposition" button covers.
export const canReleaseMaterialLotV2 = (me: Me | null) => hasPermission(me, "material_lot.release");
export const canDispositionMaterialLot = (me: Me | null) => hasPermission(me, "material_lot.disposition");

export const canAuthorRules = (me: Me | null) => hasPermission(me, "rules.author");

// supplier.create / supplier_qualification.create (Document 18) share one grant.
export const canCreateSupplier = (me: Me | null) => hasPermission(me, "supplier.create");
// material.create / .update (Document 15) share one grant.
export const canCreateMaterial = (me: Me | null) => hasPermission(me, "material.create");

export const canAuthorProduct = (me: Me | null) => hasPermission(me, "product.author");
export const canReleaseProduct = (me: Me | null) => hasPermission(me, "product.release");
export const canSuspendProduct = (me: Me | null) => hasPermission(me, "product.suspend");
export const canViewProduct = (me: Me | null) => hasPermission(me, "product.view");

export const canAuthorRecipe = (me: Me | null) => hasPermission(me, "recipe.author");
export const canReleaseRecipe = (me: Me | null) => hasPermission(me, "recipe.release");
export const canSuspendRecipe = (me: Me | null) => hasPermission(me, "recipe.suspend");
export const canViewRecipe = (me: Me | null) => hasPermission(me, "recipe.view");


// --- WP-05 QMS capabilities ---------------------------------------------------------------------
//
// Every QMS record type (deviation/CAPA/NCR/change/complaint/risk/SCAR/internal audit/field action/
// document/training/quality metric) has its own create/work/approve permission codes -- scripts/seed.py
// grants them to genuinely different role combinations per record type (e.g. ncr.create's role set is
// not complaint.create's), so there is no single correct "QMS write" or "QMS view" permission to check
// generically. Each list/detail page below checks its OWN record type's exact codes directly via
// hasPermission -- see each page's own PERMISSION_FOR_TRANSITION-style map. This replaces four
// generic helpers this file used to export (canRaiseQualityEvent / canInvestigateQms / canApproveQms /
// canViewQms, each an approximation shared across every QMS page) -- an audit (2026-09-18) found that
// approximation wrong for several record types (e.g. NCR/complaint/CAPA/deviation create had different
// real role sets than the shared "any operational role" helper assumed), which is exactly the failure
// mode a shared coarse permission check produces once the underlying grants diverge per record type.

export const canAuthorDocument = (me: Me | null) => hasPermission(me, "document.create");
export const canReleaseDocument = (me: Me | null) => hasPermission(me, "document.release");

export const canAssignTraining = (me: Me | null) => hasPermission(me, "training.assignment.create");
export const canQualifyTraining = (me: Me | null) => hasPermission(me, "training.waiver.create");

// evidence.manifest / .legal_hold / .integrity_check (Document 72) share one grant, narrower than
// canOperateEvidence (evidence.upload, above).
export const canManageEvidenceIntegrity = (me: Me | null) => hasPermission(me, "evidence.manifest");

// --- Equipment, release, QA review, packaging, supplier ------------------------------------------

// list_assets/get_asset (Document 38) carry no evaluate_policy() call at all -- any authenticated user
// may view equipment, so this is a login check, not a permission check (there is no equipment_asset.view
// code in the catalogue).
export const canViewEquipment = (me: Me | null) => me !== null;
export const canCreateEquipment = (me: Me | null) => hasPermission(me, "equipment_asset.create");
export const canCalibrateEquipment = (me: Me | null) => hasPermission(me, "equipment_asset.calibrate");
export const canMaintainEquipment = (me: Me | null) => hasPermission(me, "equipment_asset.maintain");
export const canHoldEquipment = (me: Me | null) => hasPermission(me, "equipment_asset.hold");
export const canReturnEquipmentToService = (me: Me | null) => hasPermission(me, "equipment_asset.return_to_service");

// OOS/OOT (Document 25). canInvestigateOos gates 5 buttons (lab investigation / classify lab cause /
// retest plan / resample plan / impact) that scripts/seed.py grants as one identical bundle to
// Admin + QA Reviewer + QC Reviewer -- oos_record.lab_investigation is representative of that whole
// bundle. canDispositionOos likewise covers both "Approve disposition" (oos_record.disposition) and
// "Close OOS" (oos_record.close), an identical Admin + QA Releaser grant.
export const canInvestigateOos = (me: Me | null) => hasPermission(me, "oos_record.lab_investigation");
export const canExtendOos = (me: Me | null) => hasPermission(me, "oos_record.extended_investigation");
export const canDispositionOos = (me: Me | null) => hasPermission(me, "oos_record.disposition");

// yield/reconciliation (Document 17).
export const canEvaluateYield = (me: Me | null) => hasPermission(me, "yield_calculation.evaluate");
export const canVerifyReconciliation = (me: Me | null) => hasPermission(me, "reconciliation.verify");

export const canViewRelease = (me: Me | null) => hasPermission(me, "release.view");
export const canEvaluateRelease = (me: Me | null) => hasPermission(me, "release.evaluate");
export const canDecideRelease = (me: Me | null) => hasPermission(me, "release.release");

export const canViewQaReview = (me: Me | null) => hasPermission(me, "qa_review.view");
export const canExecuteQaReview = (me: Me | null) => hasPermission(me, "qa_review.execute");

export const canViewGenealogy = (me: Me | null) => hasPermission(me, "genealogy.view");
export const canViewDevices = (me: Me | null) => hasPermission(me, "device.view");
export const canCreateDevice = (me: Me | null) => hasPermission(me, "device.create");
export const canExecuteDevice = (me: Me | null) => hasPermission(me, "device.execute");
export const canExecutePackaging = (me: Me | null) => hasPermission(me, "packaging.execute");
export const canApproveSupplier = (me: Me | null) => hasPermission(me, "supplier_qualification.approve");

// --- Shared QMS record shapes --------------------------------------------------------------------
//
// Every WP-05 aggregate lists through the same envelope and shares this header. Per-record extras are
// declared on the specific interfaces below; detail responses additionally carry the record's JSON
// blocks, which are rendered by JsonPanel rather than typed field-by-field (their schema is set per
// record by the owning command).

export interface QmsRecordBase {
  id: string;
  site_id: string;
  quality_event_id: string;
  state: string;
  version: number;
  created_at: string;
  closed_at: string | null;
}

export interface Deviation extends QmsRecordBase {
  deviation_number: string;
  deviation_type: string;
  source_type: string;
  source_id: string;
  source_version: number | null;
  severity: string;
  // Nullable since the auto-deviation-on-out-of-range fix: a system-opened deviation starts unassigned.
  owner_subject_id: string | null;
  investigator_subject_id: string | null;
  planned: boolean;
  disposition_code: string | null;
  capa_required: boolean | null;
  change_control_required: boolean;
  training_required: boolean;
  due_date: string | null;
}

export interface Capa extends QmsRecordBase {
  capa_number: string;
  source_type: string;
  source_id: string;
  problem_statement: string;
  scope_type: string;
  risk_class: string;
  owner_subject_id: string;
  target_date: string | null;
}

export interface CapaAction {
  id: string;
  capa_id: string;
  action_type: string;
  description: string;
  owner_subject_id: string;
  due_date: string | null;
  implementation_evidence: Record<string, unknown> | null;
  state: string;
  verification_status: string | null;
  verified_by: string | null;
  verified_at: string | null;
  version: number;
  created_at: string;
}

export interface Nonconformance extends QmsRecordBase {
  ncr_number: string;
  source_type: string | null;
  source_id: string | null;
  scope_type: string;
  defect_code: string;
  severity: string;
  owner_subject_id: string;
  capa_required: boolean | null;
  release_blocker_active: boolean;
}

export interface ChangeControl extends QmsRecordBase {
  change_number: string;
  change_type: string;
  classification: string;
  reason: string;
  owner_subject_id: string;
  emergency: boolean;
  retrospective_review_completed: boolean;
  effective_at: string | null;
}

export interface Complaint extends QmsRecordBase {
  complaint_number: string;
  received_at: string;
  source_channel: string;
  product_ref: string | null;
  nature_code: string;
  description: string;
  constituent_classification: string | null;
  investigation_required: boolean | null;
  investigation_conclusion: string | null;
  is_potential_duplicate: boolean;
}

export interface SupplierCase extends QmsRecordBase {
  case_number: string;
  supplier_id: string;
  supplier_site_id: string | null;
  material_id: string | null;
  affected_lots: unknown[];
  defect_code: string;
  severity: string;
  internal_owner_subject_id: string;
}

export interface Scar {
  id: string;
  site_id: string;
  case_id: string;
  scar_number: string;
  issued_at: string;
  due_date: string | null;
  problem_statement: string;
  requalification_required: boolean;
  source_status_decision: string | null;
  capa_required: boolean;
  is_repeat_issue: boolean;
  state: string;
  version: number;
  created_at: string;
  closed_at: string | null;
}

export interface FieldAction extends QmsRecordBase {
  action_number: string;
  action_type: string;
  risk_assessment_ref: string | null;
  capa_required: boolean;
  capa_rationale: string | null;
  revision: number;
}

export interface InternalAudit {
  id: string;
  site_id: string;
  quality_event_id: string;
  audit_number: string;
  program_ref: string;
  lead_auditor_id: string;
  team: unknown[] | null;
  auditees: unknown[] | null;
  scheduled_at: string;
  actual_start_at: string | null;
  actual_end_at: string | null;
  state: string;
  version: number;
  created_at: string;
}

export interface AuditFinding {
  id: string;
  site_id: string;
  audit_id: string;
  finding_number: string;
  requirement_ref: string;
  observation: string;
  severity: string;
  owner_subject_id: string;
  due_date: string | null;
  capa_required: boolean;
  is_repeat_finding: boolean;
  state: string;
  version: number;
  created_at: string;
  closed_at: string | null;
}

export interface RiskRecord {
  id: string;
  site_id: string;
  quality_event_id: string;
  risk_number: string;
  risk_type: string;
  hazard_problem: string;
  potential_effect: string;
  owner_subject_id: string;
  next_review_due_at: string | null;
  state: string;
  version: number;
  created_at: string;
}

// --- Equipment (Document 38) ---------------------------------------------------------------------

export interface EquipmentAsset {
  id: string;
  site_id: string;
  equipment_code: string;
  equipment_class_id: string | null;
  manufacturer: string | null;
  model: string | null;
  serial_no: string | null;
  state: string;
  qualification_status: string | null;
  calibration_status: string | null;
  next_calibration_due_date: string | null;
  maintenance_status: string | null;
  next_maintenance_due_date: string | null;
  cleanliness_status: string | null;
  hold_flag: boolean;
  hold_reason: string | null;
  hold_source: string | null;
  dedicated: boolean | null;
  firmware_version: string | null;
  version: number;
}

export interface EquipmentArea {
  id: string;
  site_id: string;
  area_code: string;
  area_type: string | null;
  classification: string | null;
  criticality: string | null;
  cleanliness_status: string | null;
  status: string;
}

// --- Packaging (Document 16) and supplier quality (Document 18) -----------------------------------

export interface PackagingRun {
  id: string;
  site_id: string;
  batch_id: string;
  product_version_id: string;
  line_ref: string | null;
  state: string;
  version: number;
  line_clearance_completed: boolean;
  reconciliation_state: string;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface Supplier {
  id: string;
  supplier_code: string;
  legal_name: string;
  role_type: string;
  status: string;
  country: string | null;
  version: number;
  created_at: string;
}

// --- Formatting ----------------------------------------------------------------------------------

/** Dates in this app are always backend ISO-8601 strings. Rendered in the viewer's locale, date only —
 * QMS due dates and schedules are day-precision decisions, and a time component just adds noise. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

/** Date and time, for audit-facing timestamps where the moment actually matters. */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

/** True when a due date has passed. Used to flag overdue rows without inventing a backend field. */
export function isOverdue(dueDate: string | null | undefined): boolean {
  if (!dueDate) return false;
  const date = new Date(dueDate);
  return !Number.isNaN(date.getTime()) && date.getTime() < Date.now();
}
