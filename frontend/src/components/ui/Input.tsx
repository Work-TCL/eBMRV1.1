import { forwardRef, type InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { error, className, ...rest },
  ref
) {
  return (
    <input
      ref={ref}
      className={`input${error ? " is-error" : ""}${className ? ` ${className}` : ""}`}
      {...rest}
    />
  );
});
