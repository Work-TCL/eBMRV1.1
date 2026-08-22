import type { ReactNode } from "react";
import { Icon } from "./Icon";

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  large,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  large?: boolean;
}) {
  if (!open) return null;
  return (
    <div
      className="modal-backdrop show"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className={`modal${large ? " modal-lg" : ""}`} role="dialog" aria-modal="true">
        <div className="modal-header">
          <div className="modal-title">{title}</div>
          <button className="btn-icon btn-ghost" onClick={onClose} aria-label="Close">
            <Icon name="x" />
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
}
