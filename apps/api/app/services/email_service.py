"""Email delivery service using Resend API."""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class EmailService:
    """Sends transactional emails via the Resend API."""

    async def send_recovery_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        store_name: str,
        tags: list[dict[str, str]] | None = None,
    ) -> str | None:
        """Send a cart recovery email.

        Returns the Resend email ID on success, None on failure.
        """
        from_address = f"{store_name} via Reva <noreply@mail.getreva.com>"

        payload: dict[str, Any] = {
            "from": from_address,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        if tags:
            payload["tags"] = tags

        if not settings.resend_api_key:
            logger.warning("Resend API key not configured — email not sent to %s", to_email)
            return None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {settings.resend_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if response.is_success:
                    data = response.json()
                    email_id = data.get("id")
                    logger.info("Recovery email sent: to=%s id=%s", to_email, email_id)
                    return str(email_id) if email_id else None
                else:
                    logger.error(
                        "Failed to send recovery email: to=%s status=%s body=%s",
                        to_email,
                        response.status_code,
                        response.text[:500],
                    )
                    return None
        except Exception:
            logger.exception("Error sending recovery email to %s", to_email)
            return None
