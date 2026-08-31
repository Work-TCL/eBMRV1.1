"""Document 30 — read helpers shared by document_commands.py and the router."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.qms.document_models import ControlledCopy, ControlledDocument, ControlledDocumentVersion
from app.mutation.errors import NotFoundError


async def get_document(session: AsyncSession, document_id: uuid.UUID) -> ControlledDocument:
    document = await session.get(ControlledDocument, document_id)
    if document is None:
        raise NotFoundError("Controlled document not found")
    return document


async def get_document_by_code(session: AsyncSession, document_code: str) -> ControlledDocument:
    document = (
        await session.execute(select(ControlledDocument).where(ControlledDocument.document_code == document_code))
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundError("Controlled document not found")
    return document


async def get_version(session: AsyncSession, version_id: uuid.UUID) -> ControlledDocumentVersion:
    version = await session.get(ControlledDocumentVersion, version_id)
    if version is None:
        raise NotFoundError("Controlled document version not found")
    return version


async def get_versions_for_document(session: AsyncSession, document_id: uuid.UUID) -> list[ControlledDocumentVersion]:
    return (
        (
            await session.execute(
                select(ControlledDocumentVersion)
                .where(ControlledDocumentVersion.document_id == document_id)
                .order_by(ControlledDocumentVersion.created_at)
            )
        )
        .scalars()
        .all()
    )


async def get_controlled_copies(session: AsyncSession, document_version_id: uuid.UUID) -> list[ControlledCopy]:
    return (
        (
            await session.execute(
                select(ControlledCopy)
                .where(ControlledCopy.document_version_id == document_version_id)
                .order_by(ControlledCopy.issued_at)
            )
        )
        .scalars()
        .all()
    )
