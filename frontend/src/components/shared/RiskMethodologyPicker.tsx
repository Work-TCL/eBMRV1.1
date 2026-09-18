"use client";

import { EntityPickerField } from "@/components/shared/EntityPicker";
import { useApiResource } from "@/lib/hooks";
import type { EntityOption, EntityOptionsStatus } from "@/lib/hooks";

// GET /rules/v1 — same endpoint `useEntityOptions().rules`/`.rulesByObjectId` already fetch, called here
// separately (not reused from that hook) because this field needs to filter to one `rule_type` before
// building its options, which `EntityOption[]` alone can't express (it's already flattened to
// {value,label}). A risk's `methodology_id` (`qms/risk_models.py`, FK ->
// `rules.gxp_rule_definition.rule_object_id`) must be the rule's real object id, not its `rule_id`
// business key — `rule_object_id` was added to this endpoint's response for exactly this field
// (previously absent, same "GET serializer drops field" fix pattern used across the rest of this repo).
interface ReleasedRuleRow {
  rule_object_id: string;
  rule_id: string;
  rule_type: string;
  semantic_version: string;
}

/**
 * A dropdown of released rules whose `rule_type` is `risk_methodology`, valued by `rule_object_id` — for
 * a Risk record's "Methodology ID" field, which previously asked the operator to go author a rule on
 * `/rules` and then paste its (undiscoverable, never-shown) object id back in here by hand.
 */
export function RiskMethodologyPickerField({
  value,
  onChange,
  hint,
  required,
}: {
  value: string;
  onChange: (value: string) => void;
  hint?: string;
  required?: boolean;
}) {
  const { data: rules, loading, error } = useApiResource<ReleasedRuleRow[]>("/rules/v1");
  const methodologies = (rules ?? []).filter((r) => r.rule_type === "risk_methodology");
  const options: EntityOption[] = methodologies.map((r) => ({
    value: r.rule_object_id,
    label: `${r.rule_id} v${r.semantic_version}`,
  }));
  const status: EntityOptionsStatus = error ? "error" : loading ? "loading" : options.length ? "ready" : "empty";

  return (
    <EntityPickerField
      label="Methodology"
      required={required}
      hint={hint ?? "A released rule of type risk_methodology, authored on the Rules page."}
      value={value}
      onChange={onChange}
      options={options}
      status={status}
      kind="risk methodology rule"
    />
  );
}
