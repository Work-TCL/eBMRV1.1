"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, isAdminAnywhere, listAll, listBatchesForSite, type EquipmentArea, type EquipmentAsset, type Material, type MaterialLot, type Me, type Site, type Supplier, type User } from "./api";

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
 * site. Each admin page calls this once instead of duplicating the same effect.
 * Default landing matches the root page's own choice (`app/page.tsx` sends every logged-in user to
 * `/batch-execution`) — legacy `/products`/`/batches` used to be that default until they were retired
 * (2026-09-07/2026-09-08, superseded by `/product-master`'s and `/batch-execution`'s regulated
 * draft→submit→release / create→issue→execute workflows, SG-149/SG-173). */
export function useRequireAdmin(redirectTo = "/batch-execution") {
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

// --- Foreign-key picker options ------------------------------------------------------------------
//
// The shared "load this entity list once, render it as a picker with a manual-ID fallback" pattern
// behind every batch/equipment `<Select>` in the app (DDCP, FormConsole, OpsRecordPage) — see
// `EntityOption` consumers for the loading/empty/error states each renders around this.

export type EntityOptionsStatus = "loading" | "ready" | "empty" | "error";

export interface EntityOption {
  value: string;
  label: string;
}

/** Loads one flat, unfiltered list-endpoint's rows into `EntityOption[]` — the repeated shape behind
 * every QMS quality-event picker below (deviations/complaints/capas/nonconformances/internal audits/
 * risks/rules all follow the identical "fetch once on mount, map to {value,label}, empty/error status"
 * shape `useEntityOptions`'s other fields already hand-wrote individually). Kept private to this file;
 * a field needing a *dependent* (cascading) list — e.g. QC results scoped to a chosen batch — still
 * fetches locally in its own component, the same way `inventory/page.tsx`'s container picker already
 * does, since this helper's single fixed `path` can't express that. */
function useListEntityOptions<T>(path: string, toOption: (row: T) => EntityOption): { options: EntityOption[]; status: EntityOptionsStatus } {
  const [options, setOptions] = useState<EntityOption[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    listAll<T>(path)
      .then((rows) => {
        if (cancelled) return;
        setOptions(rows.map(toOption));
        setStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `path` is a literal per call site; `toOption` is a fresh closure every render by design (it always reads the freshest labeling logic) and must not retrigger the fetch.
  }, [path]);

  return { options, status };
}

/** Populates the batch, equipment and equipment-area pickers used across write-heavy forms. Loaded once
 * per mounted form (not per field/operation), so switching an operation dropdown never re-fetches.
 * Phase-1 row counts sit inside `listAll`'s 100-row cap; a field that needs one falls back to manual ID
 * entry when a list can't be loaded, so a slow/failed fetch never blocks data entry. */
export function useEntityOptions(): {
  batches: EntityOption[];
  batchesStatus: EntityOptionsStatus;
  equipment: EntityOption[];
  equipmentStatus: EntityOptionsStatus;
  areas: EntityOption[];
  areasStatus: EntityOptionsStatus;
  users: EntityOption[];
  usersStatus: EntityOptionsStatus;
  materialLots: EntityOption[];
  materialLotsStatus: EntityOptionsStatus;
  /** `batches` narrowed to `status === "complete"` — the same single fetch, no extra request.
   * SG-149/SG-173 cutover (2026-09-08): batches now live in `ebmr.gxp_batch`, whose own lifecycle has no
   * "released" state at all — disposition is a separate concept owned by `qa_review`/`release` v1.
   * `"complete"` (batch_execution's own terminal production state) is the closest honest equivalent for
   * a picker that wants "this batch is done", not "this batch has been QA-released". Currently unused by
   * any page — kept for whichever picker needs a done/finished batch next. */
  releasedBatches: EntityOption[];
  releasedBatchesStatus: EntityOptionsStatus;
  materials: EntityOption[];
  materialsStatus: EntityOptionsStatus;
  /** Every supplier regardless of approval status — deliberately unfiltered. A material receipt's
   * supplier/manufacturer picker (Document 19) must allow picking *any* registered supplier; whether
   * it's currently approved is a coarse eligibility check the backend runs at examination time
   * (RCV-FR-005, `Supplier.status == "approved"`), producing a `source_not_approved` discrepancy hold
   * rather than blocking entry — so narrowing this list would hide exactly the case that check exists
   * to catch. The label surfaces status so the picker still shows it at a glance. */
  suppliers: EntityOption[];
  suppliersStatus: EntityOptionsStatus;
  /** RELEASED sterilization/CIP-SIP process cycle profile versions (Document 42) — the only state a
   * real cycle should be started against, same precedent as `releasedBatches`/`materialLots`. */
  sterilizationProfiles: EntityOption[];
  sterilizationProfilesStatus: EntityOptionsStatus;
  /** Same released-lot rows as `materialLots`, but valued by the lot's own human `internal_lot` code
   * instead of its database id — for a field that stores that code as a plain reference string rather
   * than a true foreign key (e.g. a sterilization load item's `item_reference`), where writing the id
   * would silently turn a human-readable reference into an opaque UUID. */
  materialLotCodes: EntityOption[];
  materialLotCodesStatus: EntityOptionsStatus;
  /** RELEASED aseptic process profile versions (Document 40) — `GET /aseptic/v1/profiles`, this
   * module's own read endpoint with no RBAC gate (2026-09-16: switched off `GET /products/v1/
   * sterile-profiles`, which required `product.view` — a permission neither Aseptic Operator nor
   * Aseptic Supervisor holds, so this field 403'd for the two roles that need it most). */
  asepticProfiles: EntityOption[];
  asepticProfilesStatus: EntityOptionsStatus;
  /** QC samples (Document 21) — every state, not just released/complete, since a deviation's "qc" source
   * type points at whichever sample triggered it (often still open). Feeds `GET /qc/v1/samples`, the same
   * browsable list `/qc`'s own Samples section reads. */
  qcSamples: EntityOption[];
  qcSamplesStatus: EntityOptionsStatus;
  /** QMS quality-event records (Document 26/24/25/23/27) — every state, unfiltered, since a picker
   * referencing one of these (a CAPA/field-action's "source"/"trigger" record, a deviation reference from
   * Yield) needs to find records in any lifecycle state, not just closed ones. Each feeds its own
   * module's already-real `GET .../v1/<plural>` list endpoint (`qms_deviation.view`/`capa.view`/etc. —
   * same policy check each module's own list page already passes). */
  deviations: EntityOption[];
  deviationsStatus: EntityOptionsStatus;
  complaints: EntityOption[];
  complaintsStatus: EntityOptionsStatus;
  capas: EntityOption[];
  capasStatus: EntityOptionsStatus;
  nonconformances: EntityOption[];
  nonconformancesStatus: EntityOptionsStatus;
  internalAudits: EntityOption[];
  internalAuditsStatus: EntityOptionsStatus;
  risks: EntityOption[];
  risksStatus: EntityOptionsStatus;
  /** Released rules (Document 22, RUL-FR-003) — one row per `rule_id` with its currently-effective
   * released version. Same feed Recipe Master's `condition_rule_id`/parameter `rule_id` pickers already
   * use (`GET /rules/v1`); centralised here so every other module referencing a rule by its `rule_id`
   * business key (Yield's potency-evaluation rule, `/rules`' own lookup box) doesn't re-implement the
   * fetch. A picker needing the rule's real object id instead (a genuine UUID FK, e.g. a Risk record's
   * `methodology_id`) fetches `/rules/v1` separately — see `RiskMethodologyPickerField` — since that
   * shape needs the raw `rule_type` to filter on, which this flattened `{value,label}` list doesn't
   * carry. */
  rules: EntityOption[];
  rulesStatus: EntityOptionsStatus;
} {
  const { siteId } = useSiteId();
  const [batches, setBatches] = useState<EntityOption[]>([]);
  const [batchesStatus, setBatchesStatus] = useState<EntityOptionsStatus>("loading");
  const [releasedBatches, setReleasedBatches] = useState<EntityOption[]>([]);
  const [releasedBatchesStatus, setReleasedBatchesStatus] = useState<EntityOptionsStatus>("loading");
  const [equipment, setEquipment] = useState<EntityOption[]>([]);
  const [equipmentStatus, setEquipmentStatus] = useState<EntityOptionsStatus>("loading");
  const [areas, setAreas] = useState<EntityOption[]>([]);
  const [areasStatus, setAreasStatus] = useState<EntityOptionsStatus>("loading");
  const [users, setUsers] = useState<EntityOption[]>([]);
  const [usersStatus, setUsersStatus] = useState<EntityOptionsStatus>("loading");
  const [materialLots, setMaterialLots] = useState<EntityOption[]>([]);
  const [materialLotsStatus, setMaterialLotsStatus] = useState<EntityOptionsStatus>("loading");
  const [materialLotCodes, setMaterialLotCodes] = useState<EntityOption[]>([]);
  const [materialLotCodesStatus, setMaterialLotCodesStatus] = useState<EntityOptionsStatus>("loading");
  const [materials, setMaterials] = useState<EntityOption[]>([]);
  const [materialsStatus, setMaterialsStatus] = useState<EntityOptionsStatus>("loading");
  const [suppliers, setSuppliers] = useState<EntityOption[]>([]);
  const [suppliersStatus, setSuppliersStatus] = useState<EntityOptionsStatus>("loading");
  const [sterilizationProfiles, setSterilizationProfiles] = useState<EntityOption[]>([]);
  const [sterilizationProfilesStatus, setSterilizationProfilesStatus] = useState<EntityOptionsStatus>("loading");
  const [asepticProfiles, setAsepticProfiles] = useState<EntityOption[]>([]);
  const [asepticProfilesStatus, setAsepticProfilesStatus] = useState<EntityOptionsStatus>("loading");
  const [qcSamples, setQcSamples] = useState<EntityOption[]>([]);
  const [qcSamplesStatus, setQcSamplesStatus] = useState<EntityOptionsStatus>("loading");

  useEffect(() => {
    if (!siteId) return;
    let cancelled = false;
    listBatchesForSite(siteId)
      .then((rows) => {
        if (cancelled) return;
        setBatches(rows.map((b) => ({ value: b.id, label: `${b.batch_number} - ${b.product_name} (${b.product_code})` })));
        setBatchesStatus(rows.length ? "ready" : "empty");
        const released = rows.filter((b) => b.status === "complete");
        setReleasedBatches(released.map((b) => ({ value: b.id, label: `${b.batch_number} - ${b.product_name} (${b.product_code})` })));
        setReleasedBatchesStatus(released.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) {
          setBatchesStatus("error");
          setReleasedBatchesStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [siteId]);

  useEffect(() => {
    let cancelled = false;
    listAll<EquipmentAsset>("/equipment/v1/assets")
      .then((rows) => {
        if (cancelled) return;
 setEquipment(rows.map((e) => ({ value: e.id, label: [e.equipment_code, e.manufacturer, e.model].filter(Boolean).join(" ") })));
        setEquipmentStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setEquipmentStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    listAll<EquipmentArea>("/equipment/v1/areas")
      .then((rows) => {
        if (cancelled) return;
 setAreas(rows.map((a) => ({ value: a.id, label: [a.area_code, a.area_type].filter(Boolean).join(" ") })));
        setAreasStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setAreasStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    listAll<User>("/users")
      .then((rows) => {
        if (cancelled) return;
        setUsers(rows.map((u) => ({ value: u.id, label: `${u.full_name} (${u.username})` })));
        setUsersStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setUsersStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    // "released" only — the same status a picked lot needs to actually pass a downstream check like
    // DDCP's constituent-handoff decide (BULK_NOT_RELEASED/PRIMARY_COMPONENT_NOT_RELEASED otherwise),
    // so an operator never picks a lot that's certain to fail.
    listAll<MaterialLot>("/material-lots", { status: "released" })
      .then((rows) => {
        if (cancelled) return;
        setMaterialLots(rows.map((l) => ({ value: l.id, label: `${l.internal_lot} - ${l.material_name} (${l.material_code})` })));
        setMaterialLotsStatus(rows.length ? "ready" : "empty");
        setMaterialLotCodes(rows.map((l) => ({ value: l.internal_lot, label: `${l.internal_lot} - ${l.material_name} (${l.material_code})` })));
        setMaterialLotCodesStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) {
          setMaterialLotsStatus("error");
          setMaterialLotCodesStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    listAll<Material>("/materials")
      .then((rows) => {
        if (cancelled) return;
        setMaterials(rows.map((m) => ({ value: m.id, label: `${m.name} (${m.code})` })));
        setMaterialsStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setMaterialsStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    listAll<Supplier>("/suppliers/v1")
      .then((rows) => {
        if (cancelled) return;
        setSuppliers(rows.map((s) => ({ value: s.id, label: `${s.legal_name} (${s.supplier_code}) - ${s.status}` })));
        setSuppliersStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setSuppliersStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    // Server default is already `state=RELEASED` (see `sterilization_router.list_profiles`) — the only
    // state a real cycle should be started against.
    listAll<{ id: string; profile_number: string; version: number; process_type: string }>(
      "/sterilization/v1/profiles",
    )
      .then((rows) => {
        if (cancelled) return;
        setSterilizationProfiles(
          rows.map((p) => ({ value: p.id, label: `${p.profile_number} v${p.version} - ${p.process_type}` })),
        );
        setSterilizationProfilesStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setSterilizationProfilesStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!siteId) return;
    let cancelled = false;
    // 2026-09-16 fix: was `GET /products/v1/sterile-profiles` (gated `product.view`) — the same feed
    // Product Master's own sterile-profile field uses, reused here on the assumption any caller of this
    // picker would also hold `product.view`. Aseptic Operator/Supervisor don't (scripts/seed.py grants
    // them nothing product-related at all), so this field 403'd for exactly the two roles that need it
    // most (Create aseptic operation's own required "Aseptic profile version" field) — `EntityPickerField`
    // silently degrades a 403 the same as a genuinely empty list (manual-entry fallback), so it read as
    // "no dropdown" rather than a loud error. Switched to `GET /aseptic/v1/profiles` — this module's own
    // read endpoint, no RBAC gate at all (any authenticated actor), so no permission dependency at all.
    // Full history (RELEASED+SUPERSEDED), filtered to RELEASED client-side to match the old behaviour.
    api
      .get<{ id: string; profile_number: string; version_no: number; state: string }[]>(
        `/aseptic/v1/profiles?site_id=${siteId}`,
      )
      .then((rows) => {
        if (cancelled) return;
        const released = rows.filter((p) => p.state === "RELEASED");
        setAsepticProfiles(released.map((p) => ({ value: p.id, label: `${p.profile_number} v${p.version_no}` })));
        setAsepticProfilesStatus(released.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setAsepticProfilesStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [siteId]);

  useEffect(() => {
    let cancelled = false;
    listAll<{ id: string; sample_number: string; sample_type: string; state: string }>("/qc/v1/samples")
      .then((rows) => {
        if (cancelled) return;
        setQcSamples(rows.map((s) => ({ value: s.id, label: `${s.sample_number} - ${s.sample_type} (${s.state})` })));
        setQcSamplesStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setQcSamplesStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const { options: deviations, status: deviationsStatus } = useListEntityOptions<{
    id: string;
    deviation_number: string;
    state: string;
  }>("/qms/v1/deviations", (d) => ({ value: d.id, label: `${d.deviation_number} (${d.state})` }));

  const { options: complaints, status: complaintsStatus } = useListEntityOptions<{
    id: string;
    complaint_number: string;
    state: string;
  }>("/qms/v1/complaints", (c) => ({ value: c.id, label: `${c.complaint_number} (${c.state})` }));

  const { options: capas, status: capasStatus } = useListEntityOptions<{
    id: string;
    capa_number: string;
    state: string;
  }>("/qms/v1/capas", (c) => ({ value: c.id, label: `${c.capa_number} (${c.state})` }));

  const { options: nonconformances, status: nonconformancesStatus } = useListEntityOptions<{
    id: string;
    ncr_number: string;
    state: string;
  }>("/qms/v1/nonconformances", (n) => ({ value: n.id, label: `${n.ncr_number} (${n.state})` }));

  const { options: internalAudits, status: internalAuditsStatus } = useListEntityOptions<{
    id: string;
    audit_number: string;
    state: string;
  }>("/qms/v1/audits", (a) => ({ value: a.id, label: `${a.audit_number} (${a.state})` }));

  const { options: risks, status: risksStatus } = useListEntityOptions<{
    id: string;
    risk_number: string;
    state: string;
  }>("/qms/v1/risks", (r) => ({ value: r.id, label: `${r.risk_number} (${r.state})` }));

  const [rules, setRules] = useState<EntityOption[]>([]);
  const [rulesStatus, setRulesStatus] = useState<EntityOptionsStatus>("loading");
  useEffect(() => {
    let cancelled = false;
    // Plain array, not the paginated envelope `listAll` expects (rules_router.get_released_rules returns
    // `list[dict]` directly, same shape as sterile-profiles above) — the same feed Recipe Master's own
    // rule pickers already use (`GET /rules/v1`).
    api
      .get<{ rule_object_id: string; rule_id: string; rule_type: string; semantic_version: string }[]>("/rules/v1")
      .then((rows) => {
        if (cancelled) return;
        setRules(rows.map((r) => ({ value: r.rule_id, label: `${r.rule_id} - ${r.rule_type} v${r.semantic_version}` })));
        setRulesStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setRulesStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    batches, batchesStatus, equipment, equipmentStatus, areas, areasStatus, users, usersStatus,
    materialLots, materialLotsStatus, releasedBatches, releasedBatchesStatus,
    materials, materialsStatus, suppliers, suppliersStatus,
    sterilizationProfiles, sterilizationProfilesStatus,
    materialLotCodes, materialLotCodesStatus,
    asepticProfiles, asepticProfilesStatus,
    qcSamples, qcSamplesStatus,
    deviations, deviationsStatus,
    complaints, complaintsStatus,
    capas, capasStatus,
    nonconformances, nonconformancesStatus,
    internalAudits, internalAuditsStatus,
    risks, risksStatus,
    rules, rulesStatus,
  };
}
