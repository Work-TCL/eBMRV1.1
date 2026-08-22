import type { ReactNode } from "react";
import { Icon } from "./Icon";

export function SignatureBlock({
  role,
  signed,
  manifest,
  hint,
}: {
  role: string;
  signed: boolean;
  manifest: ReactNode;
  hint?: ReactNode;
}) {
  return (
    <div className="sig-block" data-sig={signed ? "signed" : "blocked"}>
      <div className="sig-role">{role}</div>
      <div className="sig-manifest">
        <Icon name={signed ? "badge-check" : "pen"} />
        {manifest}
      </div>
      {hint && <div className="sig-hint">{hint}</div>}
    </div>
  );
}
