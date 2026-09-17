"use client";

import { useEffect, useState } from "react";
import { api, listAll, holdsAnyRole, newIdempotencyKey, type MutationReceipt } from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { Modal } from "@/components/ui/Modal";
import { Table } from "@/components/ui/Table";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { Tabs } from "@/components/ui/Tabs";
import { Stepper, StepItem, type StepMarkerState } from "@/components/ui/Stepper";
import { DDCP_FAMILIES, type DdcpFamily, type DdcpOp } from "@/components/ddcp/catalog";
import { DdcpFieldControl, DdcpFieldsGrid, ProfilePickerField, type EntityCtx, type ProfileSummary } from "@/components/ddcp/DdcpFieldControl";
import { useDdcpEntityOptions } from "@/components/ddcp/entityOptions";
import { ReadinessPanel } from "@/components/ddcp/ReadinessPanel";
import { ReadinessDetailPanel, GenealogyPanel, ReviewSummaryPanel } from "@/components/ddcp/DdcpDetailPanels";
import { friendlyDdcpError } from "@/components/ddcp/errorMessages";
import {
  buildPayload,
  initState,
  isFieldFilled,
  isFormComplete,
  type DdcpField,
  type DdcpFormState,
  type FieldValue,
  type KvRow,
  type RefValue,
  type RepeatRow,
  type SelectOption,
} from "@/components/ddcp/fields";

// Only 2 of Product Master's 5 manufacturing-profile codes name a DDCP family unambiguously (SG-175's
// own residual gap, §19 #25 of the demo guide): "drug_eluting_device" is one example coated-device
// subtype, not exhaustive, and "device" is too generic to mean autoinjector specifically -- guessing
// either mapping would violate CLAUDE.md §4. Auto-detect only ever fires for these 2; every other batch
// still needs its family picked by hand, exactly like today.
const MANUFACTURING_PROFILE_TO_FAMILY: Record<string, string> = {
  injectable_ddcp: "pfs",
  inhalation_ddcp: "inh",
};

export default function DdcpPage() {
  const { me } = useMe();
  const [typeKey, setTypeKey] = useState(DDCP_FAMILIES[0].key);
  const family = DDCP_FAMILIES.find((t) => t.key === typeKey)!;
  // §19 #33's own finding: no query param, link or copy-button bridges /batch-execution's batch detail
  // to this page -- a tester had to manually select/copy the batch UUID, come here, pick the right
  // family by hand (no auto-detect), then paste it into the Batch field, every single time. Reads via
  // window.location.search rather than next/navigation's useSearchParams() for the same reason
  // recipe-master/page.tsx's own ?openFamily= read does (SG-149 #35) -- avoids a Suspense-boundary
  // requirement this page has no other reason for.
  const [batchIdFromQuery] = useState<string | null>(() =>
    typeof window === "undefined" ? null : new URLSearchParams(window.location.search).get("batch_id")
  );
  useEffect(() => {
    if (!batchIdFromQuery) return;
    let cancelled = false;
    (async () => {
      try {
        const batch = await api.get<{ product_version_id: string }>(`/batches/v1/${batchIdFromQuery}`);
        const product = await api.get<{ manufacturing_profile_code: string }>(`/products/v1/${batch.product_version_id}`);
        const detected = MANUFACTURING_PROFILE_TO_FAMILY[product.manufacturing_profile_code];
        if (!cancelled && detected) setTypeKey(detected);
      } catch {
        // Auto-detect is a convenience only -- e.g. DDCP Operator lacking product.view, or the batch/
        // product no longer resolving. The family picker just stays on its default; batch_id below
        // still pre-fills once a family is picked by hand.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [batchIdFromQuery]);
  // Split to match the real backend RBAC split (scripts/seed.py's ROLE_PERMISSIONS, Document 54 §4):
  // "DDCP Engineer" authors/releases the profile master; "DDCP Operator" performs every execution-time
  // action, including release-readiness evaluation and evidence export (ddcp_release.evaluate/export).
  // Previously this checked ["Admin", "QA Reviewer", "Supervisor"] — copied from the QMS
  // investigate-role convention rather than DDCP's own roles, so neither the actually-permissioned
  // DDCP Engineer/Operator roles could reach these cards, nor did QA Reviewer/Supervisor actually hold
  // any ddcp_* permission (their submits 403'd despite the form being shown) — see
  // docs/testing/DDCP_Manual_Test_Guide_Gujarati.md §4.3/§17 for how this was found.
  const canAuthorProfile = holdsAnyRole(me, ["Admin", "DDCP Engineer"]);
  const canExecute = holdsAnyRole(me, ["Admin", "DDCP Operator"]);
  const entities = useDdcpEntityOptions();
  // Shared across cards so a profile ID created in Card 1 pre-fills wherever Card 2/3 ask for one —
  // the user still sees and can overwrite the field, this only saves the copy/paste.
  const [lastProfileId, setLastProfileId] = useState<string | null>(null);

  return (
    <div>
      <PageHead
        title="DDCP product profiles"
        subtitle="Drug/device combination-product profiles: design, batch readiness, execution and release."
      />

      <Card pad className="mb-4">
 <Field label="Product family" hint="Each product family has its own profile, batch and execution rules pick the one you're working with.">
          <Select
            value={typeKey}
            onChange={(e) => {
              setTypeKey(e.target.value);
              setLastProfileId(null);
            }}
            style={{ maxWidth: 360, width: "100%" }}
          >
            {DDCP_FAMILIES.map((t) => (
              <option key={t.key} value={t.key}>
                {t.label}
              </option>
            ))}
          </Select>
        </Field>
      </Card>

      {batchIdFromQuery && (
        <Banner tone="info" title="Batch pre-filled from link">
          Opened from a batch link — the Batch field on the tabs below is already filled in with{" "}
          <span className="tabular">{batchIdFromQuery}</span>. If this isn&apos;t a Prefilled syringe/
          injectable or Inhalation product, pick the right family above yourself — it can&apos;t be
          auto-detected for Autoinjector/Coated device yet (SG-175).
        </Banner>
      )}

      {!canAuthorProfile && !canExecute && (
        <Banner tone="info" title="Read-only">
          Authoring and releasing profiles needs the DDCP Engineer role; recording batch execution and
          evaluating release readiness needs the DDCP Operator role.
        </Banner>
      )}
      {!canAuthorProfile && canExecute && (
        <Banner tone="info" title="Profile designer hidden">
        Authoring and releasing profiles needs the DDCP Engineer role - you can still record batch
          execution and evaluate release readiness below.
        </Banner>
      )}
      {canAuthorProfile && !canExecute && (
        <Banner tone="info" title="Execution hidden">
        Recording batch execution and evaluating release readiness needs the DDCP Operator role - you
          can still design and release profiles above.
        </Banner>
      )}

      {/* Tabs instead of three stacked cards - the page was a long scroll even for a single family, and
       * a role missing one capability (§4 of the Gujarati test guide) used to leave a visible gap where
       * that card would have been instead of just not offering that tab. `Tabs` keeps every panel
       * mounted (only toggling CSS visibility), so form state in a background tab survives a switch.
       * Content is still remounted on every family switch (via `key`) so no field value, selected
       * operation or result from one product family ever lingers into another. Keys are prefixed per
       * card — React's children reconciliation treats every keyed sibling in one tab list as one set
       * regardless of element type, so the tabs must not share a bare `family.key`. */}
      <Tabs
        initial="batch"
        tabs={[
          ...(canAuthorProfile
            ? [
                {
                  id: "profile",
                  label: "Profile designer",
                  content: (
                    <ProfileCard key={`profile-${family.key}`} family={family} entities={entities} onProfileCreated={setLastProfileId} />
                  ),
                },
              ]
            : []),
          {
            id: "batch",
            label: "Batch readiness & release",
            content: (
              <BatchCard key={`batch-${family.key}`} family={family} canAuthor={canExecute} entities={entities} defaultProfileId={lastProfileId} defaultBatchId={batchIdFromQuery} />
            ),
          },
          ...(canExecute
            ? [
                {
                  id: "execution",
                  label: "Execution & result records",
                  content: (
                    <ExecutionCard key={`exec-${family.key}`} family={family} entities={entities} defaultProfileId={lastProfileId} defaultBatchId={batchIdFromQuery} />
                  ),
                },
              ]
            : []),
          ...(family.hasChangeLinkage || family.hasComplaintTraceBySerial || family.hasComplaintTraceByBatch
            ? [
                {
                  id: "diagnostics",
                  label: "Diagnostics",
                  content: <DiagnosticsCard key={`diag-${family.key}`} family={family} />,
                },
              ]
            : []),
        ]}
      />
    </div>
  );
}

/** A bare action Button sitting beside a `Field`/`ProfilePickerField` in an `items-start` row has no
 * label of its own, so without help it sits flush with the row's top — level with the other items'
 * *labels*, not their inputs. A same-height invisible `.label` closes that gap using the real label's
 * own CSS rather than a hardcoded pixel offset, so it stays correct if the label's font or spacing ever
 * changes. See the Release/Look-up rows in `ProfileCard` for why the row uses items-start at all. */
function RowButtonSlot({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col">
      <span className="label" aria-hidden="true" style={{ visibility: "hidden" }}>
        &nbsp;
      </span>
      {children}
    </div>
  );
}

// --- Card 1: Profile designer -----------------------------------------------------------------------

function ProfileCard({
  family,
  entities,
  onProfileCreated,
}: {
  family: DdcpFamily;
  entities: EntityCtx; // profile fields never render a batch/equipment picker; passed through only for a uniform DdcpFieldsGrid call.
  onProfileCreated: (id: string) => void;
}) {
  const { siteId } = useSiteId();
  const [state, setState] = useState<DdcpFormState>(() => initState(family.profileFields));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newId, setNewId] = useState<string | null>(null);

  const [releaseId, setReleaseId] = useState("");
  // Bumped after a successful create so the release/lookup pickers refetch and include the profile
  // just created — otherwise it wouldn't appear until the next remount, even though `releaseId` is
  // already pre-filled with its id.
  const [profileListVersion, setProfileListVersion] = useState(0);
  const [expectedVersion, setExpectedVersion] = useState("1");
  const [changeRef, setChangeRef] = useState("");
  const [releaseBusy, setReleaseBusy] = useState(false);
  const [releaseResult, setReleaseResult] = useState<{ ok: boolean; text: string } | null>(null);

  const [lookupId, setLookupId] = useState("");
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  // "Create profile version" under a profile_code that already has a row silently adds the next
  // version rather than erroring — correct behaviour (that's what "version" means here), but silent
  // enough that a re-used code by mistake reads as a normal create. This surfaces it as a confirmation
  // instead, naming the version it's about to add, before the POST actually happens.
  const [duplicateConfirm, setDuplicateConfirm] = useState<{ latestVersion: number; latestState: string } | null>(null);
  const [duplicateCheckBusy, setDuplicateCheckBusy] = useState(false);

  function setField(name: string, value: FieldValue) {
    setState((s) => ({ ...s, [name]: value }));
  }

  async function submitCreate(e: React.FormEvent) {
    e.preventDefault();
    const code = (state.profile_code as string | undefined)?.trim();
    if (code) {
      setDuplicateCheckBusy(true);
      try {
        const existing = await listAll<ProfileSummary>(`${family.prefix}/profiles`, { state: "" });
        const matches = existing.filter((p) => p.profile_code === code);
        if (matches.length > 0) {
          const latest = matches.reduce((a, b) => (b.version > a.version ? b : a));
          setDuplicateConfirm({ latestVersion: latest.version, latestState: latest.state });
          return; // wait for the operator to confirm (or cancel) in the modal before posting anything
        }
      } catch {
        // The check itself is a courtesy, not a gate — if it can't be answered, fall through to the
        // real create attempt, whose own success/error is authoritative regardless.
      } finally {
        setDuplicateCheckBusy(false);
      }
    }
    await doCreate();
  }

  async function doCreate() {
    setBusy(true);
    setError(null);
    setNewId(null);
    try {
      const payload = buildPayload(family.profileFields, state);
      const receipt = await api.post<MutationReceipt>(`${family.prefix}/profiles`, {
        idempotency_key: newIdempotencyKey(),
        ...(siteId ? { site_id: siteId } : {}),
        ...payload,
      });
      setNewId(receipt.aggregate_id);
      setReleaseId(receipt.aggregate_id);
      // A freshly created profile is not always version 1 — reusing an existing profile_code
      // continues that code's own version sequence (e.g. a v1 already existed, this create made v2).
      // The mutation receipt's resulting_version is the one source of truth for this row's actual
      // version; a hardcoded "1" here is exactly what produced STALE_VERSION on release before this.
      setExpectedVersion(String(receipt.resulting_version));
      setProfileListVersion((n) => n + 1);
      onProfileCreated(receipt.aggregate_id);
    } catch (err) {
      setError(friendlyDdcpError(err, "Couldn't create the profile."));
    } finally {
      setBusy(false);
    }
  }

  async function release(e: React.FormEvent) {
    e.preventDefault();
    setReleaseBusy(true);
    setReleaseResult(null);
    try {
      await api.post<MutationReceipt>(`${family.prefix}/profiles/${releaseId.trim()}/release`, {
        idempotency_key: newIdempotencyKey(),
        profile_id: releaseId.trim(),
        expected_version: Number(expectedVersion),
        change_ref: changeRef.trim() || null,
      });
      setReleaseResult({ ok: true, text: "Profile released." });
    } catch (err) {
      setReleaseResult({ ok: false, text: friendlyDdcpError(err, "Couldn't release the profile.") });
    } finally {
      setReleaseBusy(false);
    }
  }

  async function lookup(e: React.FormEvent) {
    e.preventDefault();
    setProfile(null);
    setLookupError(null);
    try {
      setProfile(await api.get<Record<string, unknown>>(`${family.prefix}/profiles/${lookupId.trim()}`));
    } catch (err) {
      setLookupError(friendlyDdcpError(err, "Couldn't look up that profile."));
    }
  }

  const createDisabled = busy || duplicateCheckBusy || !isFormComplete(family.profileFields, state);

  return (
    <Card pad className="mb-4">
      <CardHeader title="Profile designer" />
      <p className="fs-2 text-muted mb-3">
        Define this product&rsquo;s recipe before any batch can use it - what constituents it needs, and what state each must be
        in. A profile starts as a DRAFT you can still edit; releasing it locks it and makes it available to batches.
      </p>
      <form onSubmit={submitCreate}>
        <DdcpFieldsGrid fields={family.profileFields} state={state} onChange={setField} entities={entities} profilePrefix={family.prefix} />
        <div className="mt-2">
          {error && <p className="error-text mb-2">{error}</p>}
          {newId && (
            <Banner tone="ok" title="Profile version created (draft)">
            </Banner>
          )}
          <Button type="submit" variant="primary" disabled={createDisabled}>
            {duplicateCheckBusy ? "Checking…" : busy ? "Creating…" : "Create profile version"}
          </Button>
        </div>
      </form>

      {duplicateConfirm && (
        <Modal
          open
          onClose={() => setDuplicateConfirm(null)}
          title="This profile code already exists"
          footer={
            <>
              <Button variant="secondary" onClick={() => setDuplicateConfirm(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  setDuplicateConfirm(null);
                  void doCreate();
                }}
              >
                Create version {duplicateConfirm.latestVersion + 1}
              </Button>
            </>
          }
        >
          <p className="fs-2">
                Profile code <strong className="tabular">{state.profile_code as string}</strong> already has a version - the
            latest is <strong>v{duplicateConfirm.latestVersion}</strong> ({duplicateConfirm.latestState}). Creating now adds{" "}
            <strong>v{duplicateConfirm.latestVersion + 1}</strong> as a new DRAFT alongside it; it won&rsquo;t replace or
            affect the existing version until that new one is released.
          </p>
        </Modal>
      )}

      <div className="mt-4" style={{ borderTop: "1px solid var(--border-hairline)", paddingTop: "var(--space-3)" }}>
        <p className="fs-1 text-muted mb-1">Release a profile version</p>
        <p className="fs-2 text-muted mb-2">
          Releasing locks this version and makes it available to batches; any previously released version of the same
          profile code is superseded. Needs an electronic signature policy - if none is configured for DDCP release yet,
          this will be blocked by design, not by a bug.
        </p>
        {/* items-start, not items-end: the profile picker's "Can't find it? Enter ID manually" toggle is
         * an extra line below its dropdown, which items-end would bottom-align everything else in the
         * row to — dragging the Release button down to that link instead of the dropdown it belongs
         * beside. Top-aligning avoids that regardless of which field grows a trailing line; RowButtonSlot
         * gives the button a same-height invisible label so it still lines up with the real inputs. */}
        <form onSubmit={release} className="flex items-start gap-3" style={{ flexWrap: "wrap" }}>
          <div style={{ minWidth: 260, maxWidth: 360, width: "100%" }}>
            <ProfilePickerField
              field={{ name: "profile_id", label: "Profile", type: "profileSelect", required: true }}
              value={releaseId}
              onChange={(v) => setReleaseId(v as string)}
              profilePrefix={family.prefix}
              allStates
              refreshToken={profileListVersion}
              onSelectVersion={(v) => setExpectedVersion(v === null ? "" : String(v))}
            />
          </div>
 <Field label="Expected version" hint="Auto-filled from the selected profile's current version override only if you're entering a profile ID manually.">
            <Input type="number" value={expectedVersion} onChange={(e) => setExpectedVersion(e.target.value)} style={{ maxWidth: 120 }} />
          </Field>
          <Field label="Change reference">
            <Input value={changeRef} onChange={(e) => setChangeRef(e.target.value)} placeholder="e.g. CHG-2026-045" />
          </Field>
          <RowButtonSlot>
            <Button type="submit" variant="success" disabled={releaseBusy || !releaseId.trim()}>
              {releaseBusy ? "Releasing…" : "Release"}
            </Button>
          </RowButtonSlot>
        </form>
        {releaseResult && <p className={releaseResult.ok ? "fs-2 mt-2" : "error-text mt-2"}>{releaseResult.text}</p>}
      </div>

      {family.hasProfileGet && (
        <div className="mt-4" style={{ borderTop: "1px solid var(--border-hairline)", paddingTop: "var(--space-3)" }}>
          <p className="fs-1 text-muted mb-2">Look up a profile version</p>
          <form onSubmit={lookup} className="flex flex-wrap items-start gap-3">
            <div style={{ minWidth: 260, maxWidth: 360, width: "100%" }}>
              <ProfilePickerField
                field={{ name: "profile_id", label: "Profile", type: "profileSelect" }}
                value={lookupId}
                onChange={(v) => setLookupId(v as string)}
                profilePrefix={family.prefix}
                allStates
                refreshToken={profileListVersion}
              />
            </div>
            <RowButtonSlot>
              <Button type="submit" variant="secondary" disabled={!lookupId.trim()}>
                <Icon name="search" /> Look up
              </Button>
            </RowButtonSlot>
          </form>
          {lookupError && <p className="error-text mt-2">{lookupError}</p>}
          {profile && <div className="mt-3"><JsonPanel title="Profile" value={profile} /></div>}
        </div>
      )}
    </Card>
  );
}

// --- Card 2: Batch readiness & release ----------------------------------------------------------------

function BatchCard({
  family,
  canAuthor,
  entities,
  defaultProfileId,
  defaultBatchId,
}: {
  family: DdcpFamily;
  canAuthor: boolean;
  entities: EntityCtx;
  defaultProfileId: string | null;
  defaultBatchId: string | null;
}) {
  const readinessFields: DdcpField[] = [
    { name: "batch_id", label: "Batch", type: "batchSelect", required: true },
    { name: "profile_version_id", label: "Profile version", type: "profileSelect", required: true, hint: "The RELEASED profile version to check this batch against." },
    ...family.readinessExtraFields,
  ];
  const [state, setState] = useState<DdcpFormState>(() =>
    initState(readinessFields, {
      ...(defaultProfileId ? { profile_version_id: defaultProfileId } : {}),
      ...(defaultBatchId ? { batch_id: defaultBatchId } : {}),
    })
  );
  const [readiness, setReadiness] = useState<Record<string, unknown> | null>(null);
  const [genealogy, setGenealogy] = useState<Record<string, unknown> | null>(null);
  const [reviewSummary, setReviewSummary] = useState<Record<string, unknown> | null>(null);
  const [serializationCompliance, setSerializationCompliance] = useState<Record<string, unknown> | null>(null);
  const [stepSyncStatus, setStepSyncStatus] = useState<DdcpStepSyncStatus | null>(null);
  const [completingMapping, setCompletingMapping] = useState<DdcpStepSyncMapping | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function setField(name: string, value: FieldValue) {
    setState((s) => ({ ...s, [name]: value }));
  }

  async function load(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setReadiness(null);
    setGenealogy(null);
    setReviewSummary(null);
    setSerializationCompliance(null);
    setStepSyncStatus(null);
    setLoading(true);
    const payload = buildPayload(readinessFields, state);
    const { batch_id, ...query } = payload as Record<string, unknown>;
    const batchId = String(batch_id ?? "").trim();
    try {
      const q = new URLSearchParams();
      for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
      setReadiness(await api.get<Record<string, unknown>>(`${family.prefix}/batches/${batchId}/readiness?${q.toString()}`));
      if (family.hasGenealogy) setGenealogy(await api.get<Record<string, unknown>>(`${family.prefix}/batches/${batchId}/genealogy`).catch(() => null));
      if (family.hasReviewSummary)
        setReviewSummary(await api.get<Record<string, unknown>>(`${family.prefix}/batches/${batchId}/review-summary`).catch(() => null));
      // SG-180: same batch/profile query readiness already required — reused rather than asked for twice.
      if (family.hasSerializationCompliance)
        setSerializationCompliance(
          await api.get<Record<string, unknown>>(`${family.prefix}/batches/${batchId}/serialization-compliance?${q.toString()}`).catch(() => null)
        );
      if (family.hasStepSyncStatus)
        setStepSyncStatus(await api.get<DdcpStepSyncStatus>(`${family.prefix}/batches/${batchId}/step-sync-status`).catch(() => null));
    } catch (err) {
      setError(friendlyDdcpError(err, "Couldn't load batch readiness."));
    } finally {
      setLoading(false);
    }
  }

  async function runBatchAction(seg: string, label: string) {
    setActionMsg(null);
    const batchId = String(state.batch_id ?? "").trim();
    try {
      await api.post<MutationReceipt>(`${family.prefix}/batches/${batchId}/${seg}`, {
        idempotency_key: newIdempotencyKey(),
        batch_id: batchId,
      });
      setActionMsg(`✓ ${label} done.`);
    } catch (err) {
      setActionMsg(friendlyDdcpError(err, `${label} failed.`));
    }
  }

  const loadDisabled = loading || !isFormComplete(readinessFields, state);
  // Everything from the readiness response except `ready`/`blockers`, which `ReadinessPanel` already
  // renders — batch_id, profile_version_id, em_readiness, line_clearance, equipment_check, …
  const readinessDetail: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(readiness ?? {})) {
    if (k !== "ready" && k !== "blockers") readinessDetail[k] = v;
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Batch readiness & release" />
      <p className="fs-2 text-muted mb-3">
        Check whether a batch is ready for {family.label.split(" (")[0]} production, then assess release readiness and freeze
        the evidence package for QA review.
      </p>
      <form onSubmit={load}>
        <DdcpFieldsGrid fields={readinessFields} state={state} onChange={setField} entities={entities} profilePrefix={family.prefix} />
        <Button type="submit" variant="secondary" disabled={loadDisabled}>
          <Icon name="search" /> {loading ? "Loading…" : "Check readiness"}
        </Button>
      </form>
      {error && <p className="error-text mt-3">{error}</p>}

      {readiness && (
        <>
          <div className="mt-4">
            <ReadinessPanel readiness={readiness as { ready: boolean; blockers?: { code: string; message: string }[] }} />
          </div>
          {Object.keys(readinessDetail).length > 0 && (
            <div className="mt-4" style={{ borderTop: "1px solid var(--border-hairline)", paddingTop: "var(--space-3)" }}>
              <p className="fs-1 text-muted mb-2">Readiness detail</p>
              <ReadinessDetailPanel detail={readinessDetail} />
            </div>
          )}
          {genealogy && (
            <div className="mt-4" style={{ borderTop: "1px solid var(--border-hairline)", paddingTop: "var(--space-3)" }}>
              <p className="fs-1 text-muted mb-2">Genealogy</p>
              <GenealogyPanel genealogy={genealogy} />
            </div>
          )}
          {reviewSummary && (
            <div className="mt-4" style={{ borderTop: "1px solid var(--border-hairline)", paddingTop: "var(--space-3)" }}>
              <p className="fs-1 text-muted mb-2">Review summary</p>
              <ReviewSummaryPanel summary={reviewSummary} />
            </div>
          )}
          {serializationCompliance && (
            <div className="mt-4" style={{ borderTop: "1px solid var(--border-hairline)", paddingTop: "var(--space-3)" }}>
            <JsonPanel title="Serialization compliance" value={serializationCompliance} />
            </div>
          )}
          {stepSyncStatus && (
            <div className="mt-4" style={{ borderTop: "1px solid var(--border-hairline)", paddingTop: "var(--space-3)" }}>
              <p className="fs-1 text-muted mb-2">Batch / DDCP step sync status</p>
              <p className="fs-2 text-muted mb-2">
                These two execution tracks don&apos;t auto-sync — completing a DDCP action here does not
                complete its mapped batch-execution step. Use &quot;Complete this step&quot; below to run
                the real signed batch-execution complete flow without switching pages.
              </p>
              {stepSyncStatus.mappings.length === 0 ? (
                <p className="hint">No DDCP-to-step mapping is declared for this batch&apos;s recipe.</p>
              ) : (
                <Table>
                  <thead>
                    <tr>
                      <th>DDCP action</th>
                      <th>Mapped batch step</th>
                      <th>Step state</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {stepSyncStatus.mappings.map((m, i) => (
                      <tr key={`${m.ddcp_action}-${i}`}>
                        <td className="fs-2">{m.ddcp_action}</td>
                        <td className="font-semibold tabular">{m.stable_step_code}</td>
                        <td>{m.generic_step_state ? <WorkflowStatePill state={m.generic_step_state} /> : <span className="text-muted">not on this batch</span>}</td>
                        <td style={{ textAlign: "right" }}>
                          {canAuthor && m.generic_step_state && m.generic_step_state !== "complete" && m.batch_step_id && (
                            <Button size="sm" variant="primary" onClick={() => setCompletingMapping(m)}>
                              <Icon name="check-circle" /> Complete this step
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </div>
          )}
          {canAuthor && (
            <div className="flex gap-2 mt-3">
              <Button variant="primary" onClick={() => runBatchAction("release-readiness", "Release-readiness assessment")}>
                Assess release readiness
              </Button>
              <Button variant="secondary" onClick={() => runBatchAction("evidence-package", "Evidence package")}>
                Freeze evidence package
              </Button>
            </div>
          )}
          {actionMsg && <p className="fs-2 mt-2">{actionMsg}</p>}
        </>
      )}
      {completingMapping && stepSyncStatus && completingMapping.batch_step_id && completingMapping.expected_version !== null && (
        <DdcpCompleteStepModal
          batchId={stepSyncStatus.batch_id}
          mapping={completingMapping}
          onClose={() => setCompletingMapping(null)}
          onDone={() => {
            setCompletingMapping(null);
            api
              .get<DdcpStepSyncStatus>(`${family.prefix}/batches/${stepSyncStatus.batch_id}/step-sync-status`)
              .then(setStepSyncStatus)
              .catch(() => {});
          }}
        />
      )}
    </Card>
  );
}

// SG-180 shortcut (2026-09-17, project-owner-directed): triggers the exact same signed
// batch_execution complete-step flow /batch-execution itself uses — real signature challenge, real
// audit event — just launched from here instead of requiring a page switch. Does not pre-check
// required parameters/evidence the way batch-execution's own CompleteStepModal does (this page has no
// access to that step's parameter/evidence declarations) — a step that still needs those will correctly
// fail closed with the server's own PARAMETER_REQUIRED/VALIDATION_FAILED error, shown below the form.
interface DdcpStepSyncMapping {
  ddcp_action: string;
  stable_step_code: string;
  generic_step_state: string | null;
  batch_step_id: string | null;
  expected_version: number | null;
}
interface DdcpStepSyncStatus {
  batch_id: string;
  mappings: DdcpStepSyncMapping[];
}

function DdcpCompleteStepModal({
  batchId,
  mapping,
  onClose,
  onDone,
}: {
  batchId: string;
  mapping: DdcpStepSyncMapping;
  onClose: () => void;
  onDone: () => void;
}) {
  return (
    <SignatureCeremony
      open
      onClose={onClose}
      onDone={onDone}
      challengePath={`/batches/v1/${batchId}/steps/${mapping.batch_step_id}/signature-challenges`}
      action="complete"
      title={
        <span className="flex items-center gap-2">
          <Icon name="check-circle" /> Complete step - {mapping.stable_step_code}
        </span>
      }
      summary={`Mapped from DDCP action "${mapping.ddcp_action}". Completing this step is a signed act and unblocks any batch-execution step whose only remaining predecessor is this one.`}
      submitLabel="Sign & complete"
      reason="none"
      onSign={(payload) =>
        api.post(`/batches/v1/${batchId}/steps/${mapping.batch_step_id}/complete`, {
          idempotency_key: payload.idempotency_key,
          batch_id: batchId,
          step_id: mapping.batch_step_id,
          expected_version: mapping.expected_version,
          challenge_id: payload.challenge_id,
          reauth_password: payload.reauth_password,
        })
      }
    />
  );
}

// --- Diagnostics: read-only cross-reference lookups (change-linkage, complaint-trace) ----------------

function DiagnosticsCard({ family }: { family: DdcpFamily }) {
  const [objectType, setObjectType] = useState("");
  const [objectId, setObjectId] = useState("");
  const [finishedSerial, setFinishedSerial] = useState("");
  const [batchId, setBatchId] = useState("");
  const [result, setResult] = useState<{ label: string; data: unknown } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(label: string, path: string) {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult({ label, data: await api.get<unknown>(path) });
    } catch (err) {
      setError(friendlyDdcpError(err, "Lookup failed."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Diagnostics" />
      <p className="fs-2 text-muted mb-3">Read-only cross-reference lookups - nothing here records or changes anything.</p>

      {family.hasChangeLinkage && (
        <div className="mb-4" style={{ borderBottom: "1px solid var(--border-hairline)", paddingBottom: "var(--space-3)" }}>
          <p className="fs-3 font-semibold mb-2">Change linkage</p>
          <div className="grid grid-cols-2 gap-4 mb-3">
            <Field label="Object type" hint="e.g. ddcp_profile_version, pfs_fill_operation.">
              <Input value={objectType} onChange={(e) => setObjectType(e.target.value)} />
            </Field>
            <Field label="Object ID">
              <Input value={objectId} onChange={(e) => setObjectId(e.target.value)} />
            </Field>
          </div>
          <Button
            variant="secondary"
            disabled={busy || !objectType.trim() || !objectId.trim()}
            onClick={() =>
              run(
                "Change linkage",
                `${family.prefix}/change-linkage?object_type=${encodeURIComponent(objectType.trim())}&object_id=${encodeURIComponent(objectId.trim())}`
              )
            }
          >
            <Icon name="search" /> Look up
          </Button>
        </div>
      )}

      {family.hasComplaintTraceBySerial && (
        <div className="mb-4" style={{ borderBottom: "1px solid var(--border-hairline)", paddingBottom: "var(--space-3)" }}>
          <p className="fs-3 font-semibold mb-2">Complaint trace</p>
          <Field label="Finished device serial">
            <Input value={finishedSerial} onChange={(e) => setFinishedSerial(e.target.value)} style={{ maxWidth: 320 }} />
          </Field>
          <Button
            variant="secondary"
            className="mt-2"
            disabled={busy || !finishedSerial.trim()}
            onClick={() => run("Complaint trace", `${family.prefix}/complaint-trace/${encodeURIComponent(finishedSerial.trim())}`)}
          >
            <Icon name="search" /> Look up
          </Button>
        </div>
      )}

      {family.hasComplaintTraceByBatch && (
        <div className="mb-4" style={{ borderBottom: "1px solid var(--border-hairline)", paddingBottom: "var(--space-3)" }}>
          <p className="fs-3 font-semibold mb-2">Complaint trace</p>
          <Field label="Batch ID">
            <Input value={batchId} onChange={(e) => setBatchId(e.target.value)} style={{ maxWidth: 320 }} />
          </Field>
          <Button
            variant="secondary"
            className="mt-2"
            disabled={busy || !batchId.trim()}
            onClick={() => run("Complaint trace", `${family.prefix}/batches/${encodeURIComponent(batchId.trim())}/complaint-trace`)}
          >
            <Icon name="search" /> Look up
          </Button>
        </div>
      )}

      {error && <p className="error-text mt-2">{error}</p>}
      {result && (
        <div className="mt-3">
          <JsonPanel title={result.label} value={result.data} />
        </div>
      )}
    </Card>
  );
}

// --- Card 3: Execution & result records ----------------------------------------------------------------

/** The three screens of Card 3's wizard. This used to be one screen — an op dropdown sitting on top of
 * every field that op needs, all at once, with a single Submit at the bottom — which read fine for a
 * 3-field op but became a wall for an 8+ field one (fill operations, device assembly). Splitting it into
 * "pick the action" → "fill it in" → "review & submit" changes nothing about what gets captured or how
 * it's sent: `buildPayload`/the POST itself are untouched, just moved behind an explicit confirmation
 * step instead of firing the moment every required field happens to be filled. */
type WizardStep = 1 | 2 | 3;

function ExecutionCard({
  family,
  entities,
  defaultProfileId,
  defaultBatchId,
}: {
  family: DdcpFamily;
  entities: EntityCtx;
  defaultProfileId: string | null;
  defaultBatchId: string | null;
}) {
  const { siteId } = useSiteId();

  function seedState(op: DdcpOp): DdcpFormState {
    const seeds: Record<string, string> = {};
    if (defaultProfileId) {
      for (const f of op.fields) if (f.name === "profile_version_id") seeds[f.name] = defaultProfileId;
    }
    if (defaultBatchId) {
      for (const f of op.fields) if (f.name === "batch_id") seeds[f.name] = defaultBatchId;
    }
    return initState(op.fields, seeds);
  }

  const [opIndex, setOpIndex] = useState(0);
  const op = family.ops[opIndex];
  const [step, setStep] = useState<WizardStep>(1);
  // Separates "the default op (index 0) happens to be what's selected" from "nothing has been chosen
  // yet" — without it, the first card in step 1 would render pre-highlighted before anyone touched it.
  const [chosen, setChosen] = useState(false);
  const [state, setState] = useState<DdcpFormState>(() => seedState(op));
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);
  // family.ops in the order catalog.ts declares them, bucketed by each op's `group` (first appearance
  // sets the bucket's position) — turns one long flat list into a handful of labelled clusters for step 1.
  const opGroups: { name: string; items: { op: DdcpOp; index: number }[] }[] = [];
  family.ops.forEach((o, i) => {
    let bucket = opGroups.find((g) => g.name === o.group);
    if (!bucket) {
      bucket = { name: o.group, items: [] };
      opGroups.push(bucket);
    }
    bucket.items.push({ op: o, index: i });
  });
  // Every id a later op's "recordSelect" field needs (handoff_id, fill_operation_id, record_id) was
  // only ever visible in a past submit's "Record ID: …" banner, forcing a copy/paste — this remembers
  // every id created so far in this session, keyed by the producing op's `producesRecordKind` (catalog.ts),
  // so the consuming field can offer it as a dropdown instead. Session-local by design: there's no
  // backend list endpoint for these sub-resources (see DdcpOp.producesRecordKind's own comment).
  const [recentRecords, setRecentRecords] = useState<Record<string, SelectOption[]>>({});
  // Every record's latest known version, by id — every op below that names an id in its URL
  // (constituent-handoffs/{id}/decide, fill-operations/{id}/…, device-assembly/{id}/verify) also takes
  // an "Expected version" body field for optimistic concurrency, and a stale value there is exactly a
  // STALE_VERSION 409 waiting to happen — the same root cause the Release form's "Expected version" had
  // (a hardcoded default that never tracked the real record). Seeded from the mutation receipt returned
  // by whichever op created or last mutated that id, so it's always the version *this session* actually
  // produced — never guessed.
  const [recordVersions, setRecordVersions] = useState<Record<string, number>>({});
  // `recentRecords` above is pure session memory — it goes empty on a page refresh, since there's
  // nowhere else to get a handoff/assembly-record/fill-operation id from... except there is, for these
  // three kinds: genealogy already returns every handoff, assembly step and fill operation ever
  // recorded for a batch, straight from the real backend, refresh or not. This is the fallback for
  // exactly that case — "look up records for this batch" instead of being stuck re-creating something
  // that already exists.
  // Each row also carries its current `version` — genealogy is the *only* source for this id after a
  // refresh, so if this didn't seed `recordVersions` too, the "Expected version" field would silently
  // keep sitting at its "1" default for a record genealogy just proved has moved past that (this was a
  // real gap: `pfs_fill_operation` landed here with an id/label but no version, so picking one from a
  // refreshed page still produced a guaranteed STALE_VERSION on submit).
  const genealogyRecordSources: Record<string, (g: Record<string, unknown>) => (SelectOption & { version: number })[]> = {
    pfs_handoff: (g) =>
      ((g.incoming_constituents as Record<string, unknown>[] | undefined) ?? []).map((c) => ({
        value: String(c.id),
        label: `${String(c.id).slice(0, 8)}… - ${c.from_constituent}/${c.to_constituent} (${c.state})`,
        version: Number(c.version ?? 1),
      })),
    pfs_assembly_record: (g) =>
      ((g.device_assembly_chain as Record<string, unknown>[] | undefined) ?? []).map((a) => ({
        value: String(a.id),
        label: `${String(a.id).slice(0, 8)}… - ${a.assembly_step} (${a.result})`,
        version: Number(a.version ?? 1),
      })),
    pfs_fill_operation: (g) =>
      ((g.fill_operations as Record<string, unknown>[] | undefined) ?? []).map((f) => ({
        value: String(f.id),
        label: `${String(f.id).slice(0, 8)}… - ${f.fill_program_id} (${f.state})`,
        version: Number(f.version ?? 1),
      })),
  };
  const [lookupBatchId, setLookupBatchId] = useState("");
  const [genealogyOptions, setGenealogyOptions] = useState<Record<string, SelectOption[]>>({});
  const [genealogyStatus, setGenealogyStatus] = useState<"idle" | "loading" | "error">("idle");
  const lookupKind = op.fields.find((f) => f.type === "recordSelect" && f.recordKind && genealogyRecordSources[f.recordKind])?.recordKind;

  async function lookupByBatch(batchId: string) {
    setLookupBatchId(batchId);
    setGenealogyOptions({});
    if (!batchId.trim() || !family.hasGenealogy) return;
    setGenealogyStatus("loading");
    try {
      const g = await api.get<Record<string, unknown>>(`${family.prefix}/batches/${batchId.trim()}/genealogy`);
      const next: Record<string, SelectOption[]> = {};
      const versions: Record<string, number> = {};
      for (const [kind, extract] of Object.entries(genealogyRecordSources)) {
        const rows = extract(g);
        next[kind] = rows;
        for (const row of rows) versions[row.value] = row.version;
      }
      setGenealogyOptions(next);
      setRecordVersions((prev) => ({ ...prev, ...versions }));
      setGenealogyStatus("idle");
    } catch {
      setGenealogyStatus("error");
    }
  }

  // Session-created records win the "which shows first" order (they're what an operator just did);
  // genealogy fills in anything from before a refresh or from another session, de-duplicated by id.
  const mergedRecords: Record<string, SelectOption[]> = {};
  for (const kind of new Set([...Object.keys(recentRecords), ...Object.keys(genealogyOptions)])) {
    const own = recentRecords[kind] ?? [];
    const ownIds = new Set(own.map((o) => o.value));
    mergedRecords[kind] = [...own, ...(genealogyOptions[kind] ?? []).filter((o) => !ownIds.has(o.value))];
  }

  function selectOp(i: number) {
    setOpIndex(i);
    setChosen(true);
    setState(seedState(family.ops[i]));
    setResult(null);
    setStep(2);
  }

  function setField(name: string, value: FieldValue) {
    setState((s) => {
      const next = { ...s, [name]: value };
      const fieldDef = op.fields.find((f) => f.name === name);
      const knownVersion = fieldDef?.type === "recordSelect" ? recordVersions[value as string] : undefined;
      if (knownVersion !== undefined && op.fields.some((f) => f.name === "expected_version")) {
        next.expected_version = String(knownVersion);
      }
      return next;
    });
  }

  async function doSubmit() {
    setBusy(true);
    setResult(null);
    try {
      // Every DDCP sub-action that names an id in its URL (handoff_id, fill_operation_id, record_id)
      // also requires that same id in the body — the backend checks the two match — so the body is
      // built from every field, path id included, never filtered down.
      const payload = buildPayload(op.fields, state);
      const filledPath = op.path.replace(/\{(\w+)\}/g, (_, name) => encodeURIComponent(((state[name] as string) ?? "").trim()));
      const receipt = await api.post<MutationReceipt>(`${family.prefix}/${filledPath}`, {
        idempotency_key: newIdempotencyKey(),
        ...payload,
      });
      setResult({ ok: true, text: `Recorded successfully. Record ID: ${receipt.aggregate_id}` });
      // aggregate_id/resulting_version are this same record's id and its version *after* this op's own
      // mutation — true whether this op just created the record or updated an existing one (decide/ipc/
      // interventions/complete/verify all mutate the id they were given), so this one line keeps the
      // tracker correct for both cases.
      setRecordVersions((v) => ({ ...v, [receipt.aggregate_id]: receipt.resulting_version }));
      if (op.producesRecordKind) {
        const kind = op.producesRecordKind;
        const option: SelectOption = {
          value: receipt.aggregate_id,
          label: `${receipt.aggregate_id.slice(0, 8)}… - ${op.label} (${new Date().toLocaleTimeString()})`,
        };
        setRecentRecords((r) => ({ ...r, [kind]: [option, ...(r[kind] ?? [])] }));
      }
    } catch (err) {
      setResult({ ok: false, text: friendlyDdcpError(err, "That action failed.") });
    } finally {
      setBusy(false);
    }
  }

  // One handler for the whole wizard rather than a per-step onClick each: this way pressing Enter in a
  // text field on step 2 does the same thing the visible "Review" button does (advance, never submit
  // early), and pressing it again on step 3 does the same thing "Submit" does — matching what a sighted
  // mouse user sees on screen instead of introducing a keyboard-only shortcut around it.
  async function handleFormSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (step === 2) {
      if (isFormComplete(op.fields, state)) setStep(3);
      return;
    }
    if (step === 3 && !result?.ok) {
      await doSubmit();
    }
  }

  /** Plain-language rendering of one field's current value for the review step — never used to build the
   * payload (buildPayload/buildFieldValue in fields.ts remain the only source of what's actually sent).
   * Returns null for "nothing to show" (empty optional field), which the caller uses to skip the row. */
  function formatReviewValue(field: DdcpField, value: FieldValue): string | null {
    switch (field.type) {
      case "ref": {
        const v = value as RefValue;
        if (!v?.key || !v.value?.trim()) return null;
        const keyLabel = field.refKeys?.find((k) => k.value === v.key)?.label ?? v.key;
        return `${keyLabel}: ${v.value.trim()}`;
      }
      case "repeat": {
        const rows = (value as RepeatRow[] | undefined) ?? [];
        if (rows.length === 0) return null;
        const noun = field.itemLabel ?? "row";
        return `${rows.length} ${noun}${rows.length === 1 ? "" : "s"}`;
      }
      case "kv": {
        const rows = ((value as KvRow[] | undefined) ?? []).filter((r) => r.key.trim());
        if (rows.length === 0) return null;
        return rows.map((r) => `${r.key.trim()} = ${r.value || "—"}`).join(", ");
      }
      case "bool":
      case "boolKv": {
        const v = value as string;
        return v === "true" ? "Yes" : v === "false" ? "No" : null;
      }
      case "select": {
        const v = value as string;
        if (!v) return null;
        return field.options?.find((o) => o.value === v)?.label ?? v;
      }
      case "batchSelect":
        return lookupOptionLabel(entities.batches, value as string);
      case "equipmentSelect":
        return lookupOptionLabel(entities.equipment, value as string);
      case "areaSelect":
        return lookupOptionLabel(entities.areas, value as string);
      case "recordSelect":
        return lookupOptionLabel(mergedRecords[field.recordKind ?? ""] ?? [], value as string);
      default: {
        const v = (value as string | undefined)?.trim();
        return v ? v : null;
      }
    }
  }

  function markerState(n: number): StepMarkerState {
    if (step === n) return "current";
    if (step > n) return "completed";
    return "pending";
  }

  return (
    <Card pad>
      <CardHeader title="Execution & result records" />
      <p className="fs-2 text-muted mb-3">
 Record what actually happened during batch production handoffs, fills, assembly steps, tests, counts and
        dispositions - pick the action, fill it in, then confirm before it&rsquo;s sent.
      </p>

      <Stepper>
        <StepItem
          number={1}
          state={markerState(1)}
          title="What are you recording?"
          meta={chosen ? op.label : "Pick an action below"}
          action={
            step > 1 ? (
              <Button type="button" variant="ghost" size="sm" onClick={() => setStep(1)}>
                Change
              </Button>
            ) : undefined
          }
        />
        <StepItem
          number={2}
          state={markerState(2)}
          title="Enter details"
          meta={
            step === 1
              ? "—"
              : isFormComplete(op.fields, state)
              ? "Ready to review"
              : "Some required fields still empty"
          }
          action={
            step === 3 ? (
              <Button type="button" variant="ghost" size="sm" onClick={() => setStep(2)}>
                Edit
              </Button>
            ) : undefined
          }
        />
        <StepItem
          number={3}
          icon={result?.ok ? "check" : undefined}
          state={markerState(3)}
          title="Review & submit"
          meta={
            step < 3
              ? "—"
              : result
              ? result.ok
                ? "Recorded"
                : "Couldn't complete this action"
              : "Check everything below, then submit"
          }
        />
      </Stepper>

      <form onSubmit={handleFormSubmit} className="mt-4">
        {step === 1 && (
          <div>
            {opGroups.map((g) => (
              <div className="op-choice-group" key={g.name}>
                <p className="fs-1 text-muted mb-2" style={{ textTransform: "uppercase", letterSpacing: ".04em" }}>
                  {g.name}
                </p>
                <div className="op-choice-grid">
                  {g.items.map(({ op: o, index }) => (
                    <button
                      key={o.path}
                      type="button"
                      className="op-choice"
                      data-selected={chosen && index === opIndex ? "true" : undefined}
                      onClick={() => selectOp(index)}
                    >
                      <div className="op-choice-title">{o.label}</div>
                      {o.about && <div className="op-choice-about">{o.about}</div>}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {step === 2 && (
          <div>
            <div className="mb-3">
              <p className="fs-5" style={{ fontWeight: "var(--fw-bold)" }}>
                {op.label}
              </p>
              {op.about && <p className="fs-2 text-muted mt-1">{op.about}</p>}
            </div>

            {lookupKind && (
              <div className="banner mb-3" data-tone="info">
                <Icon name="info" />
                <div style={{ flex: 1 }}>
                  <p className="font-semibold">Refreshed the page? Look up the batch here first</p>
                  <p className="fs-3 mt-1 mb-2">
                    The picker below only remembers records created since your last page load - it goes empty
                    on refresh even though the records themselves are still saved. Pick the batch here to
                    reload them from its real history.
                  </p>
                  <DdcpFieldControl
                    field={{
                      name: "_lookup_batch",
                      label: "Batch",
                      type: "batchSelect",
                      hint: "Not submitted - just refills the picker below. Genealogy doesn't carry a record's version, though, so picking one this way won't auto-fill Expected version below - check the record's actual current version before submitting.",
                    }}
                    value={lookupBatchId}
                    onChange={(v) => void lookupByBatch(v as string)}
                    entities={entities}
                  />
                  {genealogyStatus === "loading" && <p className="fs-2 text-muted mt-1">Loading…</p>}
                  {genealogyStatus === "error" && <p className="error-text fs-2 mt-1">Couldn&rsquo;t load records for that batch.</p>}
                </div>
              </div>
            )}

            <DdcpFieldsGrid
              fields={op.fields}
              state={state}
              onChange={setField}
              entities={entities}
              profilePrefix={family.prefix}
              recentRecords={mergedRecords}
              siteId={siteId}
            />

            <div className="flex justify-between mt-3" style={{ flexWrap: "wrap", gap: "var(--space-2)" }}>
              <Button type="button" variant="secondary" onClick={() => setStep(1)}>
                <Icon name="arrow-left" /> Back
              </Button>
              <Button type="submit" variant="primary" disabled={!isFormComplete(op.fields, state)}>
                Review <Icon name="arrow-right" />
              </Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <div className="mb-3">
              <p className="fs-5" style={{ fontWeight: "var(--fw-bold)" }}>
                {op.label}
              </p>
              <p className="fs-2 text-muted mt-1">Check what will be sent before submitting - Back to edit any field.</p>
            </div>

            <dl className="review-list mb-3">
              {op.fields.map((f) => {
                const v = state[f.name];
                if (!isFieldFilled(f, v)) return null;
                const display = formatReviewValue(f, v);
                if (display === null) return null;
                return (
                  <div className="review-row" key={f.name}>
                    <dt>{f.label}</dt>
                    <dd>{display}</dd>
                  </div>
                );
              })}
            </dl>

            {result && (
              <Banner tone={result.ok ? "ok" : "critical"} title={result.ok ? "Recorded" : "Couldn't complete this action"}>
                {result.text}
              </Banner>
            )}

            <div className="flex justify-between mt-3" style={{ flexWrap: "wrap", gap: "var(--space-2)" }}>
              <Button type="button" variant="secondary" onClick={() => setStep(2)} disabled={busy}>
                <Icon name="arrow-left" /> Back to edit
              </Button>
              {result?.ok ? (
                <div className="flex gap-2">
                  <Button type="button" variant="secondary" onClick={() => selectOp(opIndex)}>
                    Do this again
                  </Button>
                  <Button type="button" variant="primary" onClick={() => setStep(1)}>
                    Choose a different action
                  </Button>
                </div>
              ) : (
                <Button type="submit" variant="primary" disabled={busy}>
                  {busy ? "Submitting…" : "Submit"}
                </Button>
              )}
            </div>
          </div>
        )}
      </form>
    </Card>
  );
}

function lookupOptionLabel(options: SelectOption[], value: string): string | null {
  if (!value?.trim()) return null;
  return options.find((o) => o.value === value)?.label ?? value;
}
