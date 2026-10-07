// Shared by admin/roles/[id]/page.tsx (the Advanced permission-grid editor) and
// RoleTemplateGallery.tsx (the template-first "New role" gallery) -- both need the same "which
// business-named Activities does this set of granted permissions cover" computation, previously
// inline only in the [id] edit page. See activityCatalogue.ts for what an Activity is and why it's a
// static, presentational grouping rather than a database table.

import type { Permission } from "@/lib/api";
import { ACTIVITY_CATALOGUE } from "@/lib/activityCatalogue";

// Codes are "<module>.<resource>.<action>" (e.g. "ai_governance.evaluation.run"). There's no separate
// module column in the schema, so the module is parsed from the code prefix.
export function permissionModuleKey(code: string): string {
  const idx = code.indexOf(".");
  return idx === -1 ? code : code.slice(0, idx);
}

export interface ActivityWithPermissions {
  key: string;
  label: string;
  moduleKeys: string[];
  permissions: Permission[];
}

/** Computed from the live permission catalogue, not the static ACTIVITY_CATALOGUE module-key lists
 * alone, so a module with zero permissions today never renders an empty row, and any module key not
 * yet filed under a named activity still appears (under "Other") rather than silently becoming
 * invisible through this grouping. Only activities with at least one granted permission are returned
 * when `grantedIds` is passed; pass `null` to get every non-empty activity regardless of grant state
 * (used by the template gallery's descriptive tags, before any role has been picked). */
export function computeActivities(
  allPermissions: Permission[],
  grantedIds: Set<string> | null
): ActivityWithPermissions[] {
  const covered = new Set(ACTIVITY_CATALOGUE.flatMap((a) => a.moduleKeys));
  const allModuleKeys = new Set(allPermissions.map((p) => permissionModuleKey(p.code)));
  const otherKeys = Array.from(allModuleKeys).filter((k) => !covered.has(k));
  const defs =
    otherKeys.length > 0 ? [...ACTIVITY_CATALOGUE, { key: "other", label: "Other", moduleKeys: otherKeys }] : ACTIVITY_CATALOGUE;
  return defs
    .map((a) => {
      const keySet = new Set(a.moduleKeys);
      const permissions = allPermissions.filter((p) => keySet.has(permissionModuleKey(p.code)));
      return { key: a.key, label: a.label, moduleKeys: a.moduleKeys, permissions };
    })
    .filter((a) => a.permissions.length > 0)
    .filter((a) => grantedIds === null || a.permissions.some((p) => grantedIds.has(p.id)));
}
