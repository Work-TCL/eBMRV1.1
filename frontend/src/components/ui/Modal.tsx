"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
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
  // Portalled to document.body rather than rendered inline: every caller that opens a Modal from inside
  // a page's own <form> (e.g. UomSelect's "+ Add new UOM" from materials/page.tsx's create-material
  // form) would otherwise produce a real nested <form> in the live DOM. A nested form is invalid HTML;
  // in practice a submit inside the inner form can trigger the outer form's native submit/navigation
  // too, which aborts any in-flight request (like the UOM draft POST) and looks like "the whole page
  // refreshed". Moving the DOM subtree under <body> removes the nesting entirely while leaving the React
  // tree (context, event handling) untouched, per React's own portal semantics.
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!open || !mounted) return null;
  return createPortal(
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
    </div>,
    document.body
  );
}
