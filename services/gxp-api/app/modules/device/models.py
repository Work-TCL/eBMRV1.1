"""Document 12 (SPEC-EBMR-003) — eDHR / Device Production History. New module: no legacy `device` stub
existed to be additive alongside, so this is the module's only home. See migration
0cb6e2ece7c0_0013_device_schema for the schema deviations from docs/generated/04_DATA_MODEL_CATALOGUE.md.

Only 1 of Document 12's 5 owned entities (`device_unit`) is DDL-ready; the other 4
(`device_component_usage`, `device_test_result`, `device_defect`, `device_evidence_inheritance`) are
prose-only field-name lists -- deferred as SG-049. Consequently this module only implements the slice of
DHR-FR-001..030 buildable against `device_unit` alone, without component/test/inspection/NCR/rework
tracking or the infrastructure (Equipment master, NCR/QMS, sterilization, packaging/labeling, DDCP
profiles) that most of the rest of the document depends on -- see SG-050.

State model (real Document 12 §4): `CREATED -> IN_PROCESS -> TEST_PENDING -> ACCEPTANCE_PENDING ->
ACCEPTED -> RELEASED`, alternates `HOLD, NONCONFORMING, REWORK, REJECTED, SCRAPPED`. Entry into
IN_PROCESS happens via assembly/component actions (DHR-FR-007), which depend on
device_component_usage -- not DDL-ready (SG-049) -- so it is never reached this pass; everything from
TEST_PENDING onward depends on device_test_result (SG-049) too. There is also no `scrap` or
`resume-from-hold` endpoint in the Document 12 API list (11 APIs) to expose those transitions even where
the data existed. DEVICE_STATES below is the honest buildable subset: creation and a one-way hold
directly from `created` (clearing a hold depends on the gapped accept/rework disposition path, SG-050).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

DEVICE_STATES = ("created", "hold")

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "created": {"hold"},
    "hold": set(),
}


class DeviceUnit(Base):
    __tablename__ = "device_unit"
    __table_args__ = (UniqueConstraint("site_id", "serial_number"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    product_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_product_version.id"), nullable=False
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"))
    device_lot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.device_unit.id"))
    serial_number: Mapped[str | None] = mapped_column(String(200))
    udi_di: Mapped[str | None] = mapped_column(String(120))
    udi_pi: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="created")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    release_status: Mapped[str] = mapped_column(String(40), nullable=False, default="not_released")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
