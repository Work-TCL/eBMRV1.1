"use client";

import { useState } from "react";
import { Field } from "./Field";
import { Input } from "./Input";
import { Button } from "./Button";

/** Client requirement #1: every business-code field offers Auto (server-assigned, e.g. MAT-000123) vs.
 * Manual (free entry, validated for uniqueness server-side) entry. `value`/`onChange` behave like a
 * normal controlled `Input` for the Manual case; switching to Auto reports an empty string upward so the
 * caller omits the field from its submit payload (the backend auto-generates whenever it's omitted). */
export function CodeField({
  label = "Code",
  value,
  onChange,
  required,
  hint,
}: {
  label?: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  hint?: string;
}) {
  const [mode, setMode] = useState<"auto" | "manual">("auto");

  function setModeAndValue(next: "auto" | "manual") {
    setMode(next);
    if (next === "auto") onChange("");
  }

  return (
    <Field
      label={label}
      required={required && mode === "manual"}
      hint={mode === "auto" ? "Will be assigned automatically on save." : hint}
    >
      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant={mode === "auto" ? "primary" : "ghost"}
            onClick={() => setModeAndValue("auto")}
          >
            Auto
          </Button>
          <Button
            type="button"
            size="sm"
            variant={mode === "manual" ? "primary" : "ghost"}
            onClick={() => setModeAndValue("manual")}
          >
            Manual
          </Button>
        </div>
        {mode === "manual" ? (
          <Input value={value} onChange={(e) => onChange(e.target.value)} required={required} autoFocus />
        ) : (
          <Input value="" disabled placeholder="Will be assigned on save" />
        )}
      </div>
    </Field>
  );
}
