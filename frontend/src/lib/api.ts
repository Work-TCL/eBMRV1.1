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

/** True if `me` holds the Admin role at any site — the gate for /admin and its nav entry. */
export function isAdminAnywhere(me: Me | null): boolean {
  if (!me) return false;
  return Object.values(me.roles_by_site).some((roles) => roles.includes("Admin"));
}

// Mirrors the audit.review permission grants in scripts/seed.py — Admin plus every role that reviews
// or releases regulated records. Kept here rather than derived from a permissions API call: /auth/me
// already returns roles_by_site for free, and this list changes about as often as the role catalogue.
const AUDIT_REVIEW_ROLES = ["Admin", "QA Reviewer", "QA Releaser", "QC Reviewer"];

/** True if `me` holds any role the backend grants audit.review to, at any site — the gate for the
 * Audit ledger nav entry. The endpoints enforce this for real; this only decides whether to show the
 * link instead of a guaranteed 403. */
export function canReviewAudit(me: Me | null): boolean {
  if (!me) return false;
  return Object.values(me.roles_by_site).some((roles) => roles.some((r) => AUDIT_REVIEW_ROLES.includes(r)));
}

// Mirrors scripts/seed.py's vault.review grants (Document 06) — same reviewer set as audit.
const VAULT_REVIEW_ROLES = ["Admin", "QA Reviewer", "QA Releaser", "QC Reviewer"];
// vault.correct (Document 06) — tighter: only Admin and QA Releaser.
const VAULT_CORRECT_ROLES = ["Admin", "QA Releaser"];
// rules.author / rules.release (Document 08) — Admin only this pass, no dedicated persona yet.
const RULES_AUTHOR_ROLES = ["Admin"];

export function canReviewVault(me: Me | null): boolean {
  if (!me) return false;
  return Object.values(me.roles_by_site).some((roles) => roles.some((r) => VAULT_REVIEW_ROLES.includes(r)));
}

export function canCorrectVault(me: Me | null): boolean {
  if (!me) return false;
  return Object.values(me.roles_by_site).some((roles) => roles.some((r) => VAULT_CORRECT_ROLES.includes(r)));
}

export function canAuthorRules(me: Me | null): boolean {
  if (!me) return false;
  return Object.values(me.roles_by_site).some((roles) => roles.some((r) => RULES_AUTHOR_ROLES.includes(r)));
}

// product.author / product.release / product.suspend (Document 09) — Admin only this pass, same as rules.
const PRODUCT_AUTHOR_ROLES = ["Admin"];
// product.view — everyone with any operational role, same breadth as rules.evaluate.
const PRODUCT_VIEW_ROLES = ["Admin", "Operator", "Supervisor", "QA Reviewer", "QA Releaser", "QC Reviewer"];

export function canAuthorProduct(me: Me | null): boolean {
  if (!me) return false;
  return Object.values(me.roles_by_site).some((roles) => roles.some((r) => PRODUCT_AUTHOR_ROLES.includes(r)));
}

export function canViewProduct(me: Me | null): boolean {
  if (!me) return false;
  return Object.values(me.roles_by_site).some((roles) => roles.some((r) => PRODUCT_VIEW_ROLES.includes(r)));
}

// recipe.author / recipe.release (Document 10) — Admin only this pass, same as product/rules.
const RECIPE_AUTHOR_ROLES = ["Admin"];
// recipe.view — everyone with any operational role, same breadth as product.view.
const RECIPE_VIEW_ROLES = ["Admin", "Operator", "Supervisor", "QA Reviewer", "QA Releaser", "QC Reviewer"];

export function canAuthorRecipe(me: Me | null): boolean {
  if (!me) return false;
  return Object.values(me.roles_by_site).some((roles) => roles.some((r) => RECIPE_AUTHOR_ROLES.includes(r)));
}

export function canViewRecipe(me: Me | null): boolean {
  if (!me) return false;
  return Object.values(me.roles_by_site).some((roles) => roles.some((r) => RECIPE_VIEW_ROLES.includes(r)));
}

// --- Role primitives ---------------------------------------------------------------------------
//
// The capability helpers above each re-implement the same "does `me` hold one of these roles at any
// site" test. Everything added below shares this primitive instead. As with those, the backend's
// policy engine is what actually enforces access (app/modules/policy/service.py); these only decide
// whether to render a control rather than show the user a guaranteed 403.

export function holdsAnyRole(me: Me | null, roles: readonly string[]): boolean {
  if (!me) return false;
  return Object.values(me.roles_by_site).some((held) => held.some((r) => roles.includes(r)));
}

/** Every role this deployment seeds with an operational grant — the breadth used for read-only views. */
const ALL_OPERATIONAL_ROLES = [
  "Admin", "Operator", "Supervisor", "QA Reviewer", "QA Releaser", "QC Reviewer",
] as const;

// --- WP-05 QMS capabilities ---------------------------------------------------------------------
//
// Mirrors the grants in services/gxp-api/scripts/seed.py: QMS_VIEW_CODES goes to all six operational
// roles; the write codes split by who investigates versus who approves and closes (SOD-006/SOD-007 --
// an investigator must not approve their own conclusion).

export const canViewQms = (me: Me | null) => holdsAnyRole(me, ALL_OPERATIONAL_ROLES);

/** Raising a quality event is deliberately broad — anyone on the floor can report a problem. */
export const canRaiseQualityEvent = (me: Me | null) => holdsAnyRole(me, ALL_OPERATIONAL_ROLES);

/** Triage, containment, investigation, impact — the "work the record" grants. */
export const canInvestigateQms = (me: Me | null) =>
  holdsAnyRole(me, ["Admin", "QA Reviewer", "Supervisor"]);

/** Disposition, approval, closure, effectiveness — held apart from investigation by design. */
export const canApproveQms = (me: Me | null) => holdsAnyRole(me, ["Admin", "QA Releaser"]);

/** Document control: drafting versus releasing/making effective (SOD-005). */
export const canAuthorDocument = (me: Me | null) => holdsAnyRole(me, ["Admin", "QA Reviewer"]);
export const canReleaseDocument = (me: Me | null) => holdsAnyRole(me, ["Admin", "QA Releaser"]);

/** Training: assignment versus assessment/qualification (SOD-015 forbids self-qualification). */
export const canAssignTraining = (me: Me | null) => holdsAnyRole(me, ["Admin", "Supervisor", "QA Reviewer"]);
export const canQualifyTraining = (me: Me | null) => holdsAnyRole(me, ["Admin", "QA Releaser"]);

// --- Equipment, release, QA review, packaging, supplier ------------------------------------------

export const canViewEquipment = (me: Me | null) => holdsAnyRole(me, ALL_OPERATIONAL_ROLES);
export const canCreateEquipment = (me: Me | null) => holdsAnyRole(me, ["Admin", "Equipment Administrator"]);
export const canCalibrateEquipment = (me: Me | null) =>
  holdsAnyRole(me, ["Admin", "Calibration Technician"]);
export const canMaintainEquipment = (me: Me | null) =>
  holdsAnyRole(me, ["Admin", "Maintenance Technician"]);
export const canHoldEquipment = (me: Me | null) =>
  holdsAnyRole(me, ["Admin", "Operator", "QA Reviewer", "QA Releaser"]);
export const canReturnEquipmentToService = (me: Me | null) =>
  holdsAnyRole(me, ["Admin", "QA Reviewer", "Engineering Manager"]);

export const canViewRelease = (me: Me | null) => holdsAnyRole(me, ALL_OPERATIONAL_ROLES);
export const canEvaluateRelease = (me: Me | null) =>
  holdsAnyRole(me, ["Admin", "QA Reviewer", "QA Releaser"]);
export const canDecideRelease = (me: Me | null) => holdsAnyRole(me, ["Admin", "QA Releaser"]);

export const canViewQaReview = (me: Me | null) => holdsAnyRole(me, ALL_OPERATIONAL_ROLES);
export const canExecuteQaReview = (me: Me | null) => holdsAnyRole(me, ["Admin", "QA Reviewer"]);

export const canViewGenealogy = (me: Me | null) => holdsAnyRole(me, ALL_OPERATIONAL_ROLES);
export const canViewDevices = (me: Me | null) => holdsAnyRole(me, ALL_OPERATIONAL_ROLES);
export const canExecutePackaging = (me: Me | null) =>
  holdsAnyRole(me, ["Admin", "Operator", "Supervisor"]);
export const canApproveSupplier = (me: Me | null) => holdsAnyRole(me, ["Admin", "QA Releaser"]);

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
  owner_subject_id: string;
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
