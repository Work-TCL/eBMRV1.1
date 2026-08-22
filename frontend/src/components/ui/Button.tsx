import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "success";
type Size = "sm" | "md" | "lg" | "icon";

interface CommonProps {
  variant?: Variant;
  size?: Size;
  block?: boolean;
  children: ReactNode;
  className?: string;
}

function classesFor({ variant = "secondary", size = "md", block, className }: Omit<CommonProps, "children">) {
  const sizeClass = size === "md" ? "" : ` btn-${size}`;
  return `btn btn-${variant}${sizeClass}${block ? " btn-block" : ""}${className ? ` ${className}` : ""}`;
}

type ButtonProps = CommonProps &
  ButtonHTMLAttributes<HTMLButtonElement> & {
    href?: undefined;
  };

interface LinkButtonProps extends CommonProps {
  href: string;
}

export function Button({ variant, size, block, className, children, ...rest }: ButtonProps) {
  return (
    <button className={classesFor({ variant, size, block, className })} {...rest}>
      {children}
    </button>
  );
}

export function LinkButton({ variant, size, block, className, children, href }: LinkButtonProps) {
  return (
    <Link href={href} className={classesFor({ variant, size, block, className })}>
      {children}
    </Link>
  );
}
