"use client";

import { useEffect, useState } from "react";
import { ApiError, downloadEvidence, fetchEvidenceBlob } from "@/lib/api";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

/** Inline preview for an uploaded evidence document. Images and PDFs render directly in the modal; plain
 * text renders as text; anything else (Office docs, zips, etc.) has no reliable in-browser renderer, so
 * it falls back to a clear "can't preview this, download it instead" message rather than showing a blank
 * frame or guessing. The fetched blob is always revoked on close/unmount to avoid leaking object URLs. */
export function DocumentPreviewModal({
  evidenceId,
  filename,
  mimeType,
  onClose,
}: {
  evidenceId: string;
  filename: string;
  mimeType: string;
  onClose: () => void;
}) {
  const isImage = mimeType.startsWith("image/");
  const isPdf = mimeType === "application/pdf";
  const isText = mimeType.startsWith("text/");
  const previewable = isImage || isPdf || isText;

  const [status, setStatus] = useState<"loading" | "ready" | "error">(previewable ? "loading" : "ready");
  const [error, setError] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);

  useEffect(() => {
    if (!previewable) return;
    let cancelled = false;
    let createdUrl: string | null = null;
    fetchEvidenceBlob(evidenceId)
      .then(async ({ url, blob }) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        createdUrl = url;
        if (isText) setTextContent(await blob.text());
        setBlobUrl(url);
        setStatus("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to load document");
        setStatus("error");
      });
    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [evidenceId]);

  return (
    <Modal
      open
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          <Icon name="file-text" /> {filename}
        </span>
      }
      large
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => downloadEvidence(evidenceId)}>
            <Icon name="download" /> Download
          </Button>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      }
    >
      {!previewable && (
        <div className="flex flex-col items-center justify-center gap-2" style={{ padding: "48px 0" }}>
          <Icon name="file-text" />
          <p className="hint" style={{ textAlign: "center" }}>
            Preview isn&apos;t available for this file type ({mimeType || "unknown"}). Use Download to open it.
          </p>
        </div>
      )}
      {previewable && status === "loading" && (
        <div className="flex items-center justify-center" style={{ padding: "48px 0" }}>
          <p className="hint">Loading preview…</p>
        </div>
      )}
      {previewable && status === "error" && <p className="error-text">{error}</p>}
      {previewable && status === "ready" && isImage && blobUrl && (
        <div className="flex items-center justify-center">
          {/* eslint-disable-next-line @next/next/no-img-element -- blob: URL, not a static asset Next can optimize */}
          <img src={blobUrl} alt={filename} style={{ maxWidth: "100%", maxHeight: "70vh", objectFit: "contain" }} />
        </div>
      )}
      {previewable && status === "ready" && isPdf && blobUrl && (
        <iframe
          src={blobUrl}
          title={filename}
          style={{ width: "100%", height: "70vh", border: "none", borderRadius: "var(--radius-2, 8px)" }}
        />
      )}
      {previewable && status === "ready" && isText && (
        <pre
          className="card card-pad"
          style={{ maxHeight: "70vh", overflow: "auto", whiteSpace: "pre-wrap", wordBreak: "break-word" }}
        >
          {textContent}
        </pre>
      )}
    </Modal>
  );
}
