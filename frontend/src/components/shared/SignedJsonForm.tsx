"use client";

import { useState } from "react";
import { api, ApiError, type MutationReceipt } from "@/lib/api";
import { useEntityOptions } from "@/lib/hooks";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import {
  FormFieldsGrid,
  buildFieldsBody,
  missingRequiredFields,
  seedComplexValues,
  seedFieldValues,
  type ComplexValues,
  type FormField,
} from "@/components/shared/FormConsole";

export interface SignedJsonOp {
  /** Path after `root` for the real mutation, e.g. `master-plans/{plan_id}/release`. Any `{name}`
   * placeholder is filled from a small Field row shown above the body. */
  postPath: string;
  /** Path after `root` for the signature-challenge endpoint, e.g.
   * `master-plans/{plan_id}/signature-challenges`. Usually shares the same `{name}` placeholders. */
  challengePath: string;
  label: string;
  /** The action name the challenge endpoint keys its Document 106 policy lookup on. */
  action: string;
  /** Structured fields — same vocabulary and rendering as `FormConsole`/`FormOp.fields`. Every op in
   * this module sets `cmd.<path_id> = <path_id>` server-side rather than checking path/body equality
   * (grep-verified in the validation router — unlike most other modules), so unlike `FormConsole`,
   * `fields` here never needs to repeat a `{name}` path placeholder as a body field. Preferred over
   * `template` for any op whose payload isn't genuinely free-form. */
  fields?: FormField[];
  /** Seed JSON for the body textarea — only used when `fields` is omitted (the payload is deeply
   * nested enough, e.g. release-authorization's `release_identity`, that a JSON body is the honest UI,
   * same rationale `FormConsole`'s own JSON fallback uses). */
  template?: string;
  about?: string;
  /** Set for the handful of signed-CREATE record types whose challenge response carries a
   * pre-generated id (e.g. `new_record_id`) that must be merged into the mutation body under this key
   * before submit — see `app.modules.validation.signature_support.
   * create_validation_signature_challenge_for_new_record()`. */
  mergeChallengeField?: string;
  /** Only `validated_release_authorization.authorize` needs this: its challenge is bound to a hash of
   * the full mutation body (Document 106 row 166 signs the decision itself, not a placeholder row), so
   * the challenge request must carry the exact same JSON the mutation body will. */
  mirrorBodyInChallenge?: boolean;
}

function pathParamNames(path: string): string[] {
  return Array.from(new Set(Array.from(path.matchAll(/\{(\w+)\}/g), (m) => m[1])));
}

function fillPath(path: string, values: Record<string, string>): string {
  return path.replace(/\{(\w+)\}/g, (_, name) => encodeURIComponent((values[name] ?? "").trim()));
}

/**
 * The signed counterpart to `FormConsole`, for the record types whose payload is deeply nested enough
 * that a JSON body is the honest UI (same rationale `FormConsole`'s own JSON fallback and the `/rules`
 * and `/ddcp` pages already use). Pick an operation, fill any path-id fields, edit the JSON body,
 * request a signature challenge, sign, submit. The challenge/consume/sign mechanics are
 * `SignatureCeremony`'s; this component only assembles the path and the body around it.
 */
export function SignedJsonForm({
  title,
  subtitle,
  root,
  ops,
}: {
  title: string;
  subtitle?: string;
  root: string;
  ops: SignedJsonOp[];
}) {
  const [idx, setIdx] = useState(0);
  const op = ops[idx];
  const [pathValues, setPathValues] = useState<Record<string, string>>({});
  const [values, setValues] = useState<Record<string, string>>(() => seedFieldValues(op.fields ?? []));
  const [complexValues, setComplexValues] = useState<ComplexValues>(() => seedComplexValues(op.fields ?? []));
  const [body, setBody] = useState(op.template ?? "{\n  \n}");
  const [open, setOpen] = useState(false);
  const [buildError, setBuildError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(undefined);
  const entities = useEntityOptions();
  // Snapshotted at "Request signature" time so the modal (and its challengeBody, for the one
  // content-hash-bound op) render from a fixed value rather than re-parsing form state on every render.
  const [pendingBody, setPendingBody] = useState<Record<string, unknown> | null>(null);

  function selectOp(next: number) {
    setIdx(next);
    setPathValues({});
    setValues(seedFieldValues(ops[next].fields ?? []));
    setComplexValues(seedComplexValues(ops[next].fields ?? []));
    setBody(ops[next].template ?? "{\n  \n}");
    setBuildError(null);
    setResult(undefined);
  }

  /** Structured fields never fail to "parse" (there's no free-text JSON to get wrong) — only the JSON
   * fallback path can. */
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

  const params = pathParamNames(op.postPath + " " + op.challengePath);
  // A path placeholder that's also a declared body field (required by this backend's path/body
  // equality checks — see `SignedJsonOp.fields` doc above) gets its value from the body field state,
  // not a second, separately-typed input — the user fills it once.
  const fieldNames = new Set((op.fields ?? []).map((f) => f.name));
  const standalonePathParams = params.filter((p) => !fieldNames.has(p));
  const resolvedPathValues: Record<string, string> = { ...pathValues };
  for (const p of params) if (fieldNames.has(p)) resolvedPathValues[p] = values[p] ?? "";
  const missingPathValue = standalonePathParams.some((p) => !(pathValues[p] ?? "").trim());
  const missingFieldValue = op.fields ? missingRequiredFields(op.fields, values, complexValues) : false;

  return (
    <Card pad className="mb-4">
      <CardHeader title={title} />
      {subtitle && <p className="fs-2 text-muted mb-3">{subtitle}</p>}
      <Field label="Operation">
        <Select value={idx} onChange={(e) => selectOp(Number(e.target.value))}>
          {ops.map((o, i) => (
            <option key={o.postPath + o.action} value={i}>
              {o.label}
            </option>
          ))}
        </Select>
      </Field>
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
      <Button
        type="button"
        variant="primary"
        className="mt-3"
        disabled={missingPathValue || missingFieldValue}
        onClick={() => {
          const built = tryBuildBody();
          if (built) {
            setPendingBody(built);
            setOpen(true);
          }
        }}
      >
        <Icon name="pen-line" /> Request signature &amp; submit
      </Button>
      {result !== undefined && (
        <div className="mt-3">
          <JsonPanel title="Response" value={result} />
        </div>
      )}

      {open && pendingBody && (
        <SignatureCeremony
          open={open}
          onClose={() => setOpen(false)}
          onDone={() => setOpen(false)}
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
    </Card>
  );
}
