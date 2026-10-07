"use client";

import { useState } from "react";
import { api, ApiError, newIdempotencyKey, type MutationReceipt } from "@/lib/api";
import { useEntityOptions } from "@/lib/hooks";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { Icon } from "@/components/ui/Icon";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import {
  FormFieldsGrid,
  buildFieldsBody,
  missingRequiredFields,
  seedComplexValues,
  seedFieldValues,
  type ComplexValues,
  type FormOp,
} from "@/components/shared/FormConsole";
import type { SignedJsonOp } from "@/components/shared/SignedJsonForm";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "success";

function fillPath(path: string, values: Record<string, string>): string {
  return path.replace(/\{(\w+)\}/g, (_, name) => encodeURIComponent((values[name] ?? "").trim()));
}

/**
 * One `FormOp` as a button that opens a Modal with just that operation's fields, instead of
 * `FormConsole`'s single card with an "Operation" dropdown switching between several. Reuses every
 * field-building/validation helper `FormConsole` itself uses, so behaviour (coercion, required-field
 * gating, path/body placeholder filling) stays identical — only the shell around it changes.
 */
export function OpButton({
  root,
  op,
  variant = "secondary",
}: {
  root: string;
  op: FormOp;
  variant?: ButtonVariant;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant={variant} onClick={() => setOpen(true)}>
        {op.label}
      </Button>
      {open && <OpModal root={root} op={op} onClose={() => setOpen(false)} />}
    </>
  );
}

function OpModal({ root, op, onClose }: { root: string; op: FormOp; onClose: () => void }) {
  const [values, setValues] = useState<Record<string, string>>(() => seedFieldValues(op.fields ?? []));
  const [complexValues, setComplexValues] = useState<ComplexValues>(() => seedComplexValues(op.fields ?? []));
  const [jsonBody, setJsonBody] = useState(op.template ?? "{\n  \n}");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(undefined);
  const entities = useEntityOptions();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setResult(undefined);
    try {
      const url = `${root}/${fillPath(op.path, values)}`;
      if (op.method === "GET") {
        setResult(await api.get<unknown>(url));
      } else {
        const body = op.fields ? buildFieldsBody(op.fields, values, complexValues) : jsonBody.trim() ? JSON.parse(jsonBody) : {};
        setResult(await api.post<MutationReceipt>(url, { idempotency_key: newIdempotencyKey(), ...body }));
      }
    } catch (err) {
      if (err instanceof SyntaxError) setError(`Invalid JSON: ${err.message}`);
      else setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  const missingRequired = op.fields ? missingRequiredFields(op.fields, values, complexValues) : false;

  return (
    <Modal open onClose={onClose} title={op.label} large>
      <form onSubmit={submit}>
        {op.about && <p className="fs-2 text-muted mb-3">{op.about}</p>}
        {op.fields ? (
          <FormFieldsGrid
            fields={op.fields}
            values={values}
            setValues={setValues}
            complexValues={complexValues}
            setComplexValues={setComplexValues}
            entities={entities}
          />
        ) : op.method === "GET" ? null : (
          <Field label="Payload (JSON)" hint="This operation has a nested payload - see the API contract.">
            <textarea className="input" rows={10} value={jsonBody} onChange={(e) => setJsonBody(e.target.value)} spellCheck={false} />
          </Field>
        )}
        {error && <p className="error-text mt-2">{error}</p>}
        {result !== undefined && (
          <div className="mt-3">
            <JsonPanel title="Response" value={result} />
          </div>
        )}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Close
          </Button>
          <Button type="submit" variant="primary" disabled={busy || missingRequired}>
            {busy ? "Working…" : op.method === "GET" ? "Fetch" : "Submit"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** Signed counterpart to `OpButton`, for a single `SignedJsonOp` — same fields/challenge/sign mechanics
 * `SignedJsonForm` uses for a list of ops, but as one button + modal. */
export function SignedOpButton({
  root,
  op,
  variant = "primary",
}: {
  root: string;
  op: SignedJsonOp;
  variant?: ButtonVariant;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant={variant} onClick={() => setOpen(true)}>
        <Icon name="pen" /> {op.label}
      </Button>
      {open && <SignedOpModal root={root} op={op} onClose={() => setOpen(false)} />}
    </>
  );
}

function SignedOpModal({ root, op, onClose }: { root: string; op: SignedJsonOp; onClose: () => void }) {
  const [pathValues, setPathValues] = useState<Record<string, string>>({});
  const [values, setValues] = useState<Record<string, string>>(() => seedFieldValues(op.fields ?? []));
  const [complexValues, setComplexValues] = useState<ComplexValues>(() => seedComplexValues(op.fields ?? []));
  const [body, setBody] = useState(op.template ?? "{\n  \n}");
  const [signing, setSigning] = useState(false);
  const [buildError, setBuildError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(undefined);
  const [pendingBody, setPendingBody] = useState<Record<string, unknown> | null>(null);
  const entities = useEntityOptions();

  function tryBuildBody(): Record<string, unknown> | null {
    if (op.fields) return buildFieldsBody(op.fields, values, complexValues);
    try {
      const b = body.trim() ? JSON.parse(body) : {};
      setBuildError(null);
      return b;
    } catch (err) {
      setBuildError(err instanceof Error ? `Invalid JSON: ${err.message}` : "Invalid JSON");
      return null;
    }
  }

  const params = Array.from(new Set(Array.from((op.postPath + " " + op.challengePath).matchAll(/\{(\w+)\}/g), (m) => m[1])));
  const fieldNames = new Set((op.fields ?? []).map((f) => f.name));
  const standalonePathParams = params.filter((p) => !fieldNames.has(p));
  const resolvedPathValues: Record<string, string> = { ...pathValues };
  for (const p of params) if (fieldNames.has(p)) resolvedPathValues[p] = values[p] ?? "";
  const missingPathValue = standalonePathParams.some((p) => !(pathValues[p] ?? "").trim());
  const missingFieldValue = op.fields ? missingRequiredFields(op.fields, values, complexValues) : false;

  return (
    <Modal open onClose={onClose} title={op.label} large>
      {op.about && <p className="fs-2 text-muted mb-3">{op.about}</p>}
      {standalonePathParams.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-3">
          {standalonePathParams.map((p) => (
            <Field key={p} label={p} required>
              <Input value={pathValues[p] ?? ""} onChange={(e) => setPathValues((c) => ({ ...c, [p]: e.target.value }))} />
            </Field>
          ))}
        </div>
      )}
      {op.fields ? (
        <FormFieldsGrid
          fields={op.fields}
          values={values}
          setValues={setValues}
          complexValues={complexValues}
          setComplexValues={setComplexValues}
          entities={entities}
        />
      ) : (
        <Field label="Payload (JSON)" hint="challenge_id / reauth_password / idempotency_key are added automatically after signing.">
          <textarea className="input" rows={8} value={body} onChange={(e) => setBody(e.target.value)} spellCheck={false} />
        </Field>
      )}
      {buildError && <p className="error-text mt-2">{buildError}</p>}
      {result !== undefined && (
        <div className="mt-3">
          <JsonPanel title="Response" value={result} />
        </div>
      )}
      <div className="flex justify-between gap-3 mt-3">
        <Button type="button" variant="secondary" onClick={onClose}>
          Close
        </Button>
        <Button
          type="button"
          variant="primary"
          disabled={missingPathValue || missingFieldValue}
          onClick={() => {
            const built = tryBuildBody();
            if (built) {
              setPendingBody(built);
              setSigning(true);
            }
          }}
        >
          <Icon name="pen-line" /> Request signature &amp; submit
        </Button>
      </div>

      {signing && pendingBody && (
        <SignatureCeremony
          open
          onClose={() => setSigning(false)}
          onDone={() => setSigning(false)}
          challengePath={`${root}/${fillPath(op.challengePath, resolvedPathValues)}`}
          action={op.action}
          challengeBody={op.mirrorBodyInChallenge ? pendingBody : undefined}
          title={op.label}
          summary={
            <>
              You are about to sign <strong>{op.label.toLowerCase()}</strong>
              {op.mirrorBodyInChallenge
                ? " - the challenge is bound to the exact JSON payload above; changing it after requesting the challenge invalidates it."
                : "."}
            </>
          }
          reason="none"
          onSign={async (payload) => {
            const mergedBody: Record<string, unknown> = { ...pendingBody };
            if (op.mergeChallengeField && payload[op.mergeChallengeField] !== undefined) {
              mergedBody[op.mergeChallengeField] = payload[op.mergeChallengeField];
            }
            try {
              const receipt = await api.post<MutationReceipt>(`${root}/${fillPath(op.postPath, resolvedPathValues)}`, {
                idempotency_key: payload.idempotency_key,
                ...mergedBody,
                challenge_id: payload.challenge_id,
                reauth_password: payload.reauth_password,
              });
              setResult(receipt);
              return receipt;
            } catch (err) {
              throw err instanceof ApiError ? err : new Error("Request failed");
            }
          }}
        />
      )}
    </Modal>
  );
}
