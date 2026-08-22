import { forwardRef, type SelectHTMLAttributes } from "react";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { error, className, children, ...rest },
  ref
) {
  return (
    <select
      ref={ref}
      className={`select${error ? " is-error" : ""}${className ? ` ${className}` : ""}`}
      {...rest}
    >
      {children}
    </select>
  );
});
