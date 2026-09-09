import { ApiError } from "@/lib/api";

/** Plain-language translations for the DDCP error codes documented in
 * `docs/testing/DDCP_Manual_Test_Guide_Gujarati.md` §14 — shown to the user as the primary message,
 * with the raw code kept alongside for anyone who needs to report it. Codes not listed here fall back
 * to the backend's own message rather than a guess. */
const DDCP_ERROR_MESSAGES: Record<string, string> = {
  NOT_FOUND: "That record couldn't be found. Double-check the ID and try again.",
 VALIDATION_FAILED: "That entry isn't valid see the detail below.",
  STALE_VERSION: "This record changed since you last loaded it. Reload it and try again.",
  INVALID_TRANSITION: "That action isn't allowed in this record's current state.",
  PROFILE_SCHEMA_INVALID: "That subtype or constituent type isn't recognized.",
  PROFILE_RELEASE_BLOCKED: "This profile needs at least one constituent requirement before it can be released.",
  SIGNATURE_POLICY_UNRESOLVED:
 "This action requires an electronic signature, but no signature policy is configured for it yet. This is a deliberate safety block, not a bug Quality/Regulatory must define the signature policy first.",
 REWORK_ROUTE_REQUIRED: "Rework needs a released procedure reference it's disallowed by default.",
  CONTAINER_ALREADY_USED: "This drug container is already bound to another injector unit.",
  DOSE_UNIT_BINDING_ALREADY_USED: "This dose unit is already bound to another device.",
  LINE_NOT_READY: "The equipment line isn't ready (environmental monitoring, line clearance, or equipment eligibility).",
  BULK_NOT_RELEASED: "The referenced drug/biologic batch isn't released yet.",
  PRIMARY_COMPONENT_NOT_RELEASED: "The referenced component lot isn't released yet.",
  PFS_PROFILE_NOT_EFFECTIVE: "That profile isn't RELEASED yet (it's still DRAFT or has been superseded).",
};

/** The primary user-facing message for a failed DDCP request — never a bare "422 Unprocessable
 * Entity". Falls back to the backend's own message for codes with no dedicated translation, and to a
 * generic message for anything that isn't even an ApiError (network failure, etc).
 *
 * A mapped translation is a *category* explanation (e.g. LINE_NOT_READY's three possible causes) — the
 * backend's own `message` is the one that says which of those it actually was (e.g. "EM area status is
 * not_ready"). Dropping it left every LINE_NOT_READY failure looking identical regardless of cause, so
 * both are shown together rather than the translation replacing it. */
export function friendlyDdcpError(err: unknown, fallback = "That request failed."): string {
  if (err instanceof SyntaxError) return `That value isn't valid: ${err.message}`;
  if (err instanceof ApiError) {
    const friendly = DDCP_ERROR_MESSAGES[err.code];
    return friendly ? `${friendly} ${err.message} (${err.code})` : `${err.message} (${err.code})`;
  }
  return fallback;
}
