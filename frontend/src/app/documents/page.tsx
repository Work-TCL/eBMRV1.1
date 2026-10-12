"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, canAuthorDocument, formatDate, newIdempotencyKey, pagedFetcher } from "@/lib/api";
import { useMe, useRequirePermission, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { useCommand } from "@/components/qms/QmsDetailShell";
import { humanizeLabel } from "@/lib/format";

// Matches document_router.py's _document_dict (GET /documents/v1) -- one row per controlled document
// master, distinct from the version rows shown on the per-code detail page.
interface DocumentSummary {
  id: string;
  site_id: string;
  document_code: string;
  document_type: string;
  owner_subject_id: string;
  is_external: boolean;
  external_source: string | null;
  external_revision: string | null;
  status: string;
  created_at: string;
}

const fetchDocuments = pagedFetcher<DocumentSummary>("/documents/v1");

// app/modules/qms/document_models.py DOCUMENT_TYPES.
const DOCUMENT_TYPES = ["sop", "policy", "specification", "work_instruction", "form", "external", "other"];

export default function DocumentsPage() {
  const { me } = useRequirePermission("document.view");
  const router = useRouter();
  const [draftOpen, setDraftOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const documentColumns: DataTableColumn<DocumentSummary>[] = [
    {
      key: "document_code",
      header: "Code",
      sortable: true,
      render: (d) => <span className="font-semibold tabular">{d.document_code}</span>,
    },
    { key: "document_type", header: "Type", sortable: true },
    { key: "status", header: "Status", sortable: true },
    {
      key: "external",
      header: "External",
      sortable: false,
      render: (d) => <span className="fs-2 text-muted">{d.is_external ? d.external_source ?? "Yes" : "No"}</span>,
    },
    {
      key: "created_at",
      header: "Created",
      sortable: true,
      render: (d) => <span className="tabular fs-2">{formatDate(d.created_at)}</span>,
    },
  ];

  return (
    <div>
      <PageHead
        title="Controlled documents"
        subtitle="Document versions from draft through review, release, effectivity and obsolescence."
        action={
          canAuthorDocument(me) ? (
            <Button variant="primary" onClick={() => setDraftOpen(true)}>
              <Icon name="plus" /> New draft
            </Button>
          ) : undefined
        }
      />

      <Card>
        <CardHeader title="All documents" />
        <DataTable
          columns={documentColumns}
          fetchPage={fetchDocuments}
          rowKey={(d) => d.id}
          searchPlaceholder="Search by document code…"
          emptyIcon="file-text"
          emptyMessage="No documents yet - create a draft to get started."
          defaultSort={{ by: "created_at", dir: "desc" }}
          reloadToken={reloadToken}
          onRowClick={(d) => router.push(`/documents/${encodeURIComponent(d.document_code)}`)}
        />
      </Card>

      {draftOpen && (
        <DraftModal
          onClose={() => setDraftOpen(false)}
          onDone={(code) => {
            setDraftOpen(false);
            setReloadToken((n) => n + 1);
            router.push(`/documents/${encodeURIComponent(code)}`);
          }}
        />
      )}
    </div>
  );
}

function DraftModal({ onClose, onDone }: { onClose: () => void; onDone: (code: string) => void }) {
  const { siteId } = useSiteId();
  const { me } = useMe();
  const [documentCode, setDocumentCode] = useState("");
  // Declared after documentCode: the success callback closes over it to navigate to the new draft.
  const { busy, error, run } = useCommand(() => onDone(documentCode));
  const [documentType, setDocumentType] = useState(DOCUMENT_TYPES[0]);
  const [versionLabel, setVersionLabel] = useState("1.0");
  const [contentHash, setContentHash] = useState("");
  const [isExternal, setIsExternal] = useState(false);
  const [externalSource, setExternalSource] = useState("");

  return (
    <Modal open onClose={onClose} title="New document draft" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!siteId || !me) return;
          run(() =>
            api.post("/documents/v1/drafts", {
              idempotency_key: newIdempotencyKey(),
              site_id: siteId,
              document_code: documentCode,
              document_type: documentType,
              owner_subject_id: me.user_id,
              version_label: versionLabel,
              content_hash: contentHash,
              is_external: isExternal,
              external_source: isExternal ? externalSource : null,
            })
          );
        }}
      >
        <div className="grid grid-cols-3 gap-4">
          <Field label="Document code" required>
            <Input value={documentCode} onChange={(e) => setDocumentCode(e.target.value)} placeholder="SOP-QA-001" required autoFocus />
          </Field>
          <Field label="Type" required>
            <Select value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
              {DOCUMENT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {humanizeLabel(t)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Version label" required>
            <Input value={versionLabel} onChange={(e) => setVersionLabel(e.target.value)} required />
          </Field>
        </div>
        <Field
          label="Content hash"
          required
          hint="Digest of the authored content. It is what the released version is bound to - the document body itself lives in the Vault."
        >
          <Input value={contentHash} onChange={(e) => setContentHash(e.target.value)} required />
        </Field>
        <label className="flex items-center gap-2 fs-2 mb-3">
          <input type="checkbox" checked={isExternal} onChange={(e) => setIsExternal(e.target.checked)} />
          Externally authored document
        </label>
        {isExternal && (
          <Field label="External source" required>
            <Input value={externalSource} onChange={(e) => setExternalSource(e.target.value)} required />
          </Field>
        )}
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !documentCode.trim() || !siteId}>
            {busy ? "Creating…" : "Create draft"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
