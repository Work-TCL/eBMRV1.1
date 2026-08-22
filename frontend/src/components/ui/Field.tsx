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
