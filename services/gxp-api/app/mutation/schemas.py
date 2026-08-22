import uuid

from pydantic import BaseModel, ConfigDict


class CommandEnvelope(BaseModel):
    """Every state-changing command carries an idempotency key (MUT-FR-010). Commands against an
    existing aggregate also carry expected_version (MUT-FR-009); creation commands don't need one.
    """

    model_config = ConfigDict(extra="forbid")

    idempotency_key: str


class MutationReceipt(BaseModel):
    command_id: uuid.UUID
    aggregate_id: uuid.UUID
    resulting_version: int
    audit_event_id: uuid.UUID
    signature_id: uuid.UUID | None = None
    correlation_id: uuid.UUID
