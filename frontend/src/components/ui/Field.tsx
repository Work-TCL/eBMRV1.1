import { cloneElement, isValidElement, useId, type ReactElement, type ReactNode } from "react";
import { Icon } from "./Icon";

export function Field({
  label,
  required,
  hint,
  error,
  children,
}: {
  label?: ReactNode;
  required?: boolean;
  hint?: ReactNode;
  error?: string | null;
  children: ReactNode;
}) {
  const generatedId = useId();
  const child = isValidElement(children) ? (children as ReactElement<{ id?: string }>) : null;
  const controlId = child?.props.id ?? generatedId;
  const control = child ? cloneElement(child, { id: controlId }) : children;

  return (
    <div className="field">
      {label && (
        <label className="label" htmlFor={controlId}>
          {label} {required && <span className="req">*</span>}
        </label>
      )}
      {control}
      {error ? (
        <p className="error-text">
          <Icon name="alert-circle" /> {error}
        </p>
      ) : (
        hint && <p className="hint">{hint}</p>
      )}
    </div>
  );
}

/** A bare action Button sitting beside a `Field` in an `items-start` row has no label of its own, so
 * without help it sits flush with the row's top — level with the other items' *labels*, not their
 * inputs. A same-height invisible `.label` closes that gap using the real label's own CSS rather than a
 * hardcoded pixel offset, so it stays correct if the label's font or spacing ever changes.
 *
 * Use this (with `items-start`, not `items-end`) whenever a Field in the row carries a `hint` — hint text
 * sits below the control, so items-end would bottom-align the row to the hint instead of the input,
 * dragging the button down below where it visually belongs. */
export function RowButtonSlot({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col">
      <span className="label" aria-hidden="true" style={{ visibility: "hidden" }}>
        &nbsp;
      </span>
      {children}
    </div>
  );
}
