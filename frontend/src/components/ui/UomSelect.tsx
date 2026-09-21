"use client";

import { useState } from "react";
import { api, ApiError, canAuthorRules, canReleaseRules, newIdempotencyKey } from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
import { Field } from "./Field";
import { Select } from "./Select";
import { Input } from "./Input";
import { Button } from "./Button";
import { Modal } from "./Modal";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";

interface UomOption {
  code: string;
  dimension: string;
  base_unit: string;
  precision_dp: number;
}

const ADD_NEW = "__add_new_uom__";

/** Client requirements #2/#3: a real enforced dropdown over the released `rules.gxp_uom` list (not a
 * free-text `<Input>` or `<datalist>` suggestion), with an inline "+ Add new UOM" affordance for
 * authorized users so a missing unit doesn't require leaving the page. Still submits a plain UOM code
 * string — every backend command already resolves `uom`/`uom_id` from that string, this component just
 * stops the caller from typing an arbitrary one. */
export function UomSelect({
  label = "Unit of measure",
  value,
  onChange,
  required,
  hint,
}: {
  label?: string;
  value: string;
  onChange: (code: string) => void;
  required?: boolean;
  hint?: string;
}) {
  const { me } = useMe();
  const { data, reload } = useApiResource<UomOption[]>("/rules/v1/uom");
  const [addOpen, setAddOpen] = useState(false);
  const options = data ?? [];

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    if (e.target.value === ADD_NEW) {
      setAddOpen(true);
      return;
    }
    onChange(e.target.value);
  }

  return (
    <>
      <Field label={label} required={required} hint={hint}>
        <Select value={value} onChange={handleChange} required={required}>
          <option value="">Select a unit…</option>
          {options.map((u) => (
            <option key={u.code} value={u.code}>
              {u.code} ({u.dimension})
            </option>
          ))}
          {value && !options.some((u) => u.code === value) && (
            <option value={value}>{value} (not a released unit — kept from prior entry)</option>
          )}
          {canAuthorRules(me) && <option value={ADD_NEW}>+ Add new UOM…</option>}
        </Select>
      </Field>

      {addOpen && (
        <AddUomModal
          canRelease={canReleaseRules(me)}
          onClose={() => setAddOpen(false)}
          onCreated={(code) => {
            reload();
            onChange(code);
          }}
        />
      )}
    </>
  );
}

function AddUomModal({
  onClose,
  onCreated,
  canRelease,
}: {
  onClose: () => void;
  onCreated: (code: string) => void;
  canRelease: boolean;
}) {
  const [code, setCode] = useState("");
  const [dimension, setDimension] = useState("");
  const [baseUnit, setBaseUnit] = useState("");
  const [factor, setFactor] = useState("1");
  const [offset, setOffset] = useState("0");
  const [precisionDp, setPrecisionDp] = useState("3");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [createdUomId, setCreatedUomId] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const receipt = await api.post<{ aggregate_id: string }>("/rules/v1/uom/drafts", {
        idempotency_key: newIdempotencyKey(),
        code: code.trim(),
        dimension: dimension.trim(),
        base_unit: baseUnit.trim(),
        factor: factor.trim(),
        offset: offset.trim(),
        precision_dp: Number(precisionDp),
      });
      if (canRelease) {
        // Offer the release ceremony next rather than closing — a draft UOM isn't selectable anywhere
        // else in the app (every picker only lists released units) until it's released.
        setCreatedUomId(receipt.aggregate_id);
      } else {
        onCreated(code.trim());
        onClose();
      }
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to create UOM draft");
    } finally {
      setBusy(false);
    }
  }

  if (createdUomId) {
    return (
      <SignatureCeremony
        open
        onClose={() => {
          // Drafted but not released yet — still usable via this component's own "kept from prior
          // entry" fallback once selected, same as any other draft-only UOM in the app today.
          onCreated(code.trim());
          onClose();
        }}
        onDone={() => onCreated(code.trim())}
        challengePath={`/rules/v1/uom/${createdUomId}/signature-challenges`}
        action="release"
        title="Release new unit of measure"
        summary={`Releasing ${code.trim()} makes it selectable everywhere in the app.`}
        onSign={(payload) =>
          api.post(`/rules/v1/uom/${createdUomId}/release`, { ...payload, uom_id: createdUomId })
        }
      />
    );
  }

  return (
    <Modal open onClose={onClose} title="New unit of measure">
      <form onSubmit={onSubmit}>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Code" required>
            <Input value={code} onChange={(e) => setCode(e.target.value)} required autoFocus placeholder="e.g. mL" />
          </Field>
          <Field label="Dimension" required>
            <Input
              value={dimension}
              onChange={(e) => setDimension(e.target.value)}
              required
              placeholder="e.g. volume"
            />
          </Field>
          <Field label="Base unit" required>
            <Input value={baseUnit} onChange={(e) => setBaseUnit(e.target.value)} required placeholder="e.g. L" />
          </Field>
          <Field label="Factor" required hint="Multiplier to base unit.">
            <Input value={factor} onChange={(e) => setFactor(e.target.value)} required />
          </Field>
          <Field label="Offset">
            <Input value={offset} onChange={(e) => setOffset(e.target.value)} />
          </Field>
          <Field label="Precision (dp)" required>
            <Input type="number" min={0} value={precisionDp} onChange={(e) => setPrecisionDp(e.target.value)} required />
          </Field>
        </div>
        {!canRelease && (
          <p className="hint mb-3">
            This creates a draft. It becomes selectable everywhere once an authorized reviewer releases it.
          </p>
        )}
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !code.trim() || !dimension.trim() || !baseUnit.trim()}>
            {busy ? "Creating…" : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
