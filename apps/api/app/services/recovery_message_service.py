"""AI-powered recovery email message generation."""

import logging
from typing import Any

from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# Pre-written fallback templates per step
FALLBACK_TEMPLATES: list[dict[str, str]] = [
    {
        "subject": "Did you forget something? Your cart is waiting",
        "body_html": (
            "<p>Hi {customer_name},</p>"
            "<p>Looks like you left some items in your cart. "
            "We've saved them for you — just pick up where you left off!</p>"
        ),
        "cta_text": "Complete Your Purchase",
    },
    {
        "subject": "Your items are popular — don't miss out!",
        "body_html": (
            "<p>Hi {customer_name},</p>"
            "<p>Other shoppers are eyeing the same items you left behind. "
            "Don't wait too long — complete your order while everything's still available.</p>"
        ),
        "cta_text": "Return to Cart",
    },
    {
        "subject": "Still thinking it over? Here's why customers love these items",
        "body_html": (
            "<p>Hi {customer_name},</p>"
            "<p>We noticed you haven't completed your purchase yet. "
            "These products are among our most popular — customers love them for their quality and value.</p>"
        ),
        "cta_text": "Finish Checkout",
    },
    {
        "subject": "Last chance to grab your cart items",
        "body_html": (
            "<p>Hi {customer_name},</p>"
            "<p>This is a final reminder about the items you left behind. "
            "We can only hold them for so long. Complete your purchase today!</p>"
        ),
        "cta_text": "Complete Purchase Now",
    },
]

STEP_PROMPTS = [
    (
        "Write a gentle, helpful cart recovery email (Step 1 of 4, sent 2 hours after abandonment). "
        "Tone: warm and helpful, not pushy. Focus on reminding the customer what they left behind."
    ),
    (
        "Write a cart recovery email (Step 2 of 4, sent 24 hours after abandonment). "
        "Tone: confident and reassuring. Include social proof — mention that these are popular items "
        "that other customers love."
    ),
    (
        "Write a cart recovery email (Step 3 of 4, sent 48 hours after abandonment). "
        "Tone: create a sense of urgency. Mention limited availability or that items may sell out soon."
    ),
    (
        "Write a cart recovery email (Step 4 of 4, sent 72 hours after abandonment). "
        "Tone: final, direct appeal. This is the last email — make it count. "
        "{discount_text}"
    ),
]


class RecoveryMessageService:
    """Generates AI-personalized recovery email content."""

    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            api_key=settings.openai_api_key,
        )

    async def generate_recovery_email(
        self,
        cart_items: list[dict[str, Any]],
        total_price: str,
        customer_name: str | None,
        step_index: int,
        store_name: str,
        sequence_type: str,
        discount_percent: int | None = None,
    ) -> dict[str, str]:
        """Generate a personalized recovery email.

        Returns dict with keys: subject, body_html, cta_text.
        Falls back to pre-written templates on LLM failure.
        """
        display_name = customer_name or "there"

        # Build cart summary for the prompt
        item_descriptions = []
        for item in cart_items[:5]:  # Limit to 5 items in prompt
            title = item.get("title", "Item")
            price = item.get("price", "")
            qty = item.get("quantity", 1)
            item_descriptions.append(f"- {title} (qty: {qty}, ${price})")
        cart_summary = "\n".join(item_descriptions) if item_descriptions else "- Various items"

        discount_text = ""
        if discount_percent and step_index >= 3:
            discount_text = f"Offer a {discount_percent}% discount as a final incentive."

        step_idx = min(step_index, len(STEP_PROMPTS) - 1)
        step_prompt = STEP_PROMPTS[step_idx].format(discount_text=discount_text)

        prompt = (
            f"{step_prompt}\n\n"
            f"Store: {store_name}\n"
            f"Customer name: {display_name}\n"
            f"Customer type: {sequence_type}\n"
            f"Cart total: ${total_price}\n"
            f"Cart items:\n{cart_summary}\n\n"
            f"Requirements:\n"
            f"- Return ONLY a JSON object with keys: subject, body_html, cta_text\n"
            f"- body_html should use simple HTML tags (p, strong, em) — no full HTML document\n"
            f"- Keep the subject under 60 characters\n"
            f"- Address the customer as '{display_name}'\n"
            f"- Do NOT include the cart items list in the body (they'll be rendered separately)\n"
            f"- cta_text should be 2-4 words for the call-to-action button\n"
        )

        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content
            if isinstance(content, str):
                # Parse JSON from response
                import json

                # Handle markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                result = json.loads(content)
                return {
                    "subject": result.get("subject", FALLBACK_TEMPLATES[step_idx]["subject"]),
                    "body_html": result.get("body_html", ""),
                    "cta_text": result.get("cta_text", FALLBACK_TEMPLATES[step_idx]["cta_text"]),
                }
        except Exception:
            logger.exception(
                "LLM message generation failed for step %d, using fallback", step_index
            )

        # Fallback to pre-written template
        fallback = FALLBACK_TEMPLATES[step_idx]
        return {
            "subject": fallback["subject"],
            "body_html": fallback["body_html"].format(customer_name=display_name),
            "cta_text": fallback["cta_text"],
        }
