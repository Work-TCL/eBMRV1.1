"use client";

import { useState, type CSSProperties } from "react";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { EntityOption, EntityOptionsStatus } from "@/lib/hooks";

function plural(kind: string): string {
  return /[sxz]$|[cs]h$/.test(kind) ? `${kind}es` : `${kind}s`;
}

// "user"/"unit"/"unique" etc. start with the letter u but the consonant /j/ ("yoo") sound, so they take
// "a" like any consonant word — the "starts with a vowel letter" heuristic below gets these wrong.
const CONSONANT_SOUND_EXCEPTIONS = /^(user|unit|unique|uniform|one)\b/i;

function article(kind: string): string {
  if (CONSONANT_SOUND_EXCEPTIONS.test(kind)) return "a";
  return /^[aeiou]/i.test(kind) ? "an" : "a";
}

const linkBtnStyle: CSSProperties = {
  background: "none",
  border: "none",
  padding: 0,
  color: "var(--brand-600)",
  fontSize: "var(--fs-2)",
  cursor: "pointer",
  textDecoration: "underline",
};

/**
 * A foreign-key picker: a plain `<select>` of human-readable rows once the list has loaded, with a
 * manual-ID fallback the user can always reach (a record outside the Phase-1 100-row cap, or a list
 * that genuinely can't load). Used anywhere a form needs a batch/equipment/etc. id — FormConsole,
 * OpsRecordPage and the DDCP forms all render the same loading/empty/error/manual-entry states this
 * way (spec section 8's "Foreign-Key UX" requirements), sourced from one place instead of three.
 */
export function EntityPickerField({
  label,
  required,
  hint,
  value,
  onChange,
  options,
  status,
  kind,
  placeholder,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  options: EntityOption[];
  status: EntityOptionsStatus;
  /** Used in copy: "No {kind}s available yet.", "— Select a {kind} —". */
  kind: string;
  placeholder?: string;
}) {
  const [manual, setManual] = useState(false);
  const useManual = manual || status === "error";

  if (useManual) {
    return (
 <Field label={label} required={required} hint={status === "error" ? `Couldn't load the ${kind} list enter the ID directly.` : hint}>
        <Input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder ?? `${kind} ID`} />
        {status !== "error" && (
          <button type="button" style={{ ...linkBtnStyle, marginTop: 6 }} onClick={() => setManual(false)}>
            Choose from list instead
          </button>
        )}
      </Field>
    );
  }

  if (status === "loading") {
    return (
      <Field label={label} required={required} hint={hint}>
        <Select disabled>
          <option>{`Loading ${plural(kind)}…`}</option>
        </Select>
      </Field>
    );
  }

  if (status === "empty") {
    return (
      <Field label={label} required={required} hint={`No ${plural(kind)} available yet.`}>
        <Input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder ?? `${kind} ID`} />
      </Field>
    );
  }

  return (
    <Field label={label} required={required} hint={hint}>
      <Select value={value} onChange={(e) => onChange(e.target.value)}>
 <option value="">{`Select ${article(kind)} ${kind}`}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>
      <button type="button" style={{ ...linkBtnStyle, marginTop: 6 }} onClick={() => setManual(true)}>
        Can&rsquo;t find it? Enter ID manually
      </button>
    </Field>
  );
}
