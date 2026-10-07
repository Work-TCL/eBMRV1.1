"""Client gap-analysis Phase 1 (2026-10-05): outbound email for the bulk-user-onboarding invite flow.

Deliberately stdlib-only (`smtplib`/`email`) -- no new PyPI dependency, so no Document 104 justification
is needed (see `.claude/rules/09-dependencies-sbom-license.md`: "adding a dependency to reduce coding
effort" is a forbidden pattern, and stdlib SMTP is sufficient for this use case). Each client deployment
configures its own SMTP relay via `GXP_SMTP_*` env vars (ADR-0006: one deployment per client, each with
its own infra, same as its own database).

This module never raises on a send failure -- email delivery is a best-effort convenience on top of the
account-provisioning records (iam.users, iam.user_invites), which are already committed by the time this
is called. A dropped email does not strand the client's regulated state; it just means the admin needs to
re-trigger the invite or share the link out-of-band. See AI-FR-040's "unavailability must not block a
regulated workflow" principle, applied here to an infra dependency rather than AI specifically -- the same
underlying engineering judgement (a non-authoritative side effect must not roll back a committed mutation).
"""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_smtp_configured() -> bool:
    return bool(settings.smtp_host)


def send_invite_email(*, to_address: str, full_name: str, accept_url: str) -> bool:
    """Returns True if the email was handed to the SMTP relay successfully, False otherwise (including
    when SMTP isn't configured at all) -- callers log/surface this but never fail the enclosing command
    because of it."""
    if not is_smtp_configured():
        logger.warning(
            "send_invite_email: GXP_SMTP_HOST is not configured -- skipping invite email to %s "
            "(the invite record was still created; share accept_url out-of-band: %s)",
            to_address, accept_url,
        )
        return False

    message = EmailMessage()
    message["Subject"] = "You've been invited to eBMR"
    message["From"] = settings.smtp_from_address
    message["To"] = to_address
    message.set_content(
        f"Hello {full_name},\n\n"
        f"An administrator has created an eBMR account for you. Set your password to activate it:\n\n"
        f"{accept_url}\n\n"
        f"This link expires in {settings.invite_token_expire_hours} hours and can only be used once.\n"
        f"If you weren't expecting this, you can ignore this email.\n"
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            if settings.smtp_use_tls:
                client.starttls()
            if settings.smtp_username and settings.smtp_password:
                client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning(
            "send_invite_email: failed to send invite to %s (accept_url retained for manual delivery): %s",
            to_address, exc,
        )
        return False
