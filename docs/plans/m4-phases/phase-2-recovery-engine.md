# Phase 2: Recovery Engine & Sequences

> **Parent:** [M4 Cart Recovery Agent](../m4-cart-recovery.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 1 complete (webhook handling)

---

## Goal

Build the core recovery engine that orchestrates multi-touch sequences, generates personalized AI messages, and manages recovery timing across multiple channels.

---

## Tasks

### 2.1 Recovery Sequence Engine

**Location:** `apps/api/app/services/recovery.py`

- [ ] Create RecoverySequence model and state management
- [ ] Implement sequence progression logic (1hr → 2hr → 24hr → 48hr → 72hr)
- [ ] Handle sequence interruption (customer purchases, opts out)
- [ ] Support different sequence types (first-time vs returning customer)
- [ ] Add sequence performance tracking

**Recovery sequence model:**

```python
from enum import Enum
from datetime import datetime, timedelta
from app.models.base import BaseModel

class SequenceType(str, Enum):
    FIRST_TIME = "first_time"
    RETURNING = "returning"
    HIGH_VALUE = "high_value"
    LOW_STOCK = "low_stock"

class SequenceStep(str, Enum):
    POPUP_1H = "popup_1h"
    EMAIL_2H = "email_2h"
    EMAIL_24H = "email_24h"
    EMAIL_48H = "email_48h"
    EMAIL_72H = "email_72h"

class RecoverySequence(BaseModel):
    cart_id: UUID
    sequence_type: SequenceType
    current_step: SequenceStep | None = None
    steps_completed: list[SequenceStep] = []
    started_at: datetime
    completed_at: datetime | None = None
    stopped_reason: str | None = None  # "purchased", "opted_out", "expired"

    def get_next_step(self) -> SequenceStep | None:
        """Get the next step in the sequence."""
        all_steps = [
            SequenceStep.POPUP_1H,
            SequenceStep.EMAIL_2H,
            SequenceStep.EMAIL_24H,
            SequenceStep.EMAIL_48H,
            SequenceStep.EMAIL_72H
        ]

        for step in all_steps:
            if step not in self.steps_completed:
                return step
        return None

    def get_step_delay(self, step: SequenceStep) -> timedelta:
        """Get delay before executing step."""
        delays = {
            SequenceStep.POPUP_1H: timedelta(hours=1),
            SequenceStep.EMAIL_2H: timedelta(hours=2),
            SequenceStep.EMAIL_24H: timedelta(hours=24),
            SequenceStep.EMAIL_48H: timedelta(hours=48),
            SequenceStep.EMAIL_72H: timedelta(hours=72)
        }
        return delays[step]
```

### 2.2 AI Message Generation

**Location:** `apps/api/app/services/recovery_messages.py`

- [ ] Generate personalized recovery messages using OpenAI
- [ ] Customize messages based on cart contents and customer history
- [ ] Implement different message tones (helpful, urgent, incentive-based)
- [ ] Add product-specific messaging (reviews, stock levels)
- [ ] Support multiple languages based on store locale

**Message generation service:**

```python
from openai import AsyncOpenAI
from app.models.cart import Cart
from app.models.customer import Customer

class RecoveryMessageGenerator:
    def __init__(self):
        self.client = AsyncOpenAI()

    async def generate_message(
        self,
        cart: Cart,
        step: SequenceStep,
        customer: Customer | None = None
    ) -> dict[str, str]:
        """Generate personalized recovery message."""

        # Build context about cart and customer
        context = self._build_context(cart, customer)

        # Get step-specific prompt
        prompt = self._get_step_prompt(step, context)

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        message = response.choices[0].message.content

        return {
            "subject": self._extract_subject(message),
            "body": self._extract_body(message),
            "cta_text": self._extract_cta(message)
        }

    def _get_system_prompt(self) -> str:
        return """You are a helpful e-commerce assistant creating cart recovery messages.

        Guidelines:
        - Be personal and helpful, not pushy
        - Reference specific products in the cart
        - Address likely customer concerns
        - Include clear call-to-action
        - Match the store's brand tone

        Format your response as:
        SUBJECT: [email subject line]
        BODY: [email body content]
        CTA: [call-to-action button text]
        """

    def _get_step_prompt(self, step: SequenceStep, context: dict) -> str:
        prompts = {
            SequenceStep.EMAIL_2H: f"""
            Create a helpful cart recovery email for a customer who abandoned their cart 2 hours ago.

            Cart details: {context['cart_summary']}
            Customer: {context['customer_type']}

            Focus: Be helpful and answer potential questions. Gentle reminder tone.
            """,

            SequenceStep.EMAIL_24H: f"""
            Create a social proof cart recovery email for a customer who abandoned their cart 24 hours ago.

            Cart details: {context['cart_summary']}
            Customer: {context['customer_type']}

            Focus: Include customer reviews, testimonials, or popularity indicators.
            """,

            SequenceStep.EMAIL_72H: f"""
            Create a final offer cart recovery email with incentive for a customer who abandoned their cart 72 hours ago.

            Cart details: {context['cart_summary']}
            Customer: {context['customer_type']}

            Focus: Last chance messaging with discount offer. Create urgency.
            """
        }
        return prompts.get(step, "Create a cart recovery message.")
```

### 2.3 Sequence Scheduler

**Location:** `apps/api/app/workers/recovery_tasks.py`

- [ ] Create Celery tasks for each sequence step
- [ ] Implement time-delayed task execution
- [ ] Handle task cancellation when customer purchases
- [ ] Add task retry logic for failed deliveries
- [ ] Track task execution and performance

**Celery tasks:**

```python
from celery import current_app as celery_app
from datetime import datetime, timedelta
from app.services.recovery import RecoverySequence
from app.services.recovery_messages import RecoveryMessageGenerator
from app.services.email import EmailService

@celery_app.task(bind=True)
async def start_recovery_sequence(self, cart_id: str):
    """Start a new recovery sequence for abandoned cart."""
    try:
        cart = await Cart.get(cart_id)
        if not cart or cart.status != CartStatus.ABANDONED:
            return

        # Determine sequence type
        sequence_type = determine_sequence_type(cart)

        # Create sequence record
        sequence = RecoverySequence(
            cart_id=cart.id,
            sequence_type=sequence_type,
            started_at=datetime.utcnow()
        )
        await sequence.save()

        # Schedule first step (1-hour popup)
        schedule_sequence_step.apply_async(
            args=[sequence.id, SequenceStep.POPUP_1H],
            countdown=3600  # 1 hour
        )

    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)

@celery_app.task(bind=True)
async def schedule_sequence_step(self, sequence_id: str, step: str):
    """Execute a specific step in the recovery sequence."""
    try:
        sequence = await RecoverySequence.get(sequence_id)
        if not sequence or sequence.completed_at:
            return  # Sequence was stopped/completed

        cart = await Cart.get(sequence.cart_id)
        if cart.status == CartStatus.COMPLETED:
            await stop_recovery_sequence(sequence_id, "purchased")
            return

        # Execute the step
        if step == SequenceStep.POPUP_1H:
            await handle_popup_step(sequence, cart)
        elif step.startswith("email_"):
            await handle_email_step(sequence, cart, step)

        # Mark step as completed
        sequence.steps_completed.append(step)
        sequence.current_step = step
        await sequence.save()

        # Schedule next step
        next_step = sequence.get_next_step()
        if next_step:
            delay = sequence.get_step_delay(next_step)
            schedule_sequence_step.apply_async(
                args=[sequence_id, next_step],
                countdown=int(delay.total_seconds())
            )
        else:
            # Sequence complete
            sequence.completed_at = datetime.utcnow()
            await sequence.save()

    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)

async def handle_email_step(sequence: RecoverySequence, cart: Cart, step: str):
    """Handle email delivery for recovery step."""
    if not cart.customer_email:
        return  # Skip if no email

    # Generate personalized message
    generator = RecoveryMessageGenerator()
    message = await generator.generate_message(cart, step)

    # Send email
    email_service = EmailService()
    await email_service.send_recovery_email(
        to_email=cart.customer_email,
        subject=message["subject"],
        body=message["body"],
        cart=cart,
        sequence=sequence
    )
```

### 2.4 Customer Segmentation

**Location:** `apps/api/app/services/customer_segmentation.py`

- [ ] Analyze customer purchase history
- [ ] Segment by customer lifetime value
- [ ] Identify first-time vs returning customers
- [ ] Calculate optimal send times per customer
- [ ] Track customer engagement preferences

**Segmentation logic:**

```python
from app.models.customer import Customer
from app.models.order import Order

class CustomerSegmentation:
    async def determine_sequence_type(self, cart: Cart) -> SequenceType:
        """Determine the best recovery sequence for this customer."""

        customer = await self.get_customer_profile(cart)

        # First-time customer
        if not customer or customer.order_count == 0:
            return SequenceType.FIRST_TIME

        # High-value customer (>$500 lifetime value)
        if customer.lifetime_value > 500:
            return SequenceType.HIGH_VALUE

        # Low stock urgency
        if await self.has_low_stock_items(cart):
            return SequenceType.LOW_STOCK

        # Default returning customer
        return SequenceType.RETURNING

    async def get_optimal_send_time(self, customer: Customer) -> int:
        """Get optimal hour to send emails (0-23)."""
        if not customer:
            return 10  # Default 10 AM

        # Analyze past email engagement times
        engagement_hours = await self.analyze_engagement_times(customer)
        return max(engagement_hours, key=engagement_hours.get) if engagement_hours else 10
```

### 2.5 Recovery Analytics

**Location:** `apps/api/app/services/recovery_analytics.py`

- [ ] Track sequence performance metrics
- [ ] Calculate recovery rates by sequence type
- [ ] Monitor email open/click rates
- [ ] Measure revenue attribution
- [ ] Generate recovery performance reports

**Analytics tracking:**

```python
from app.models.analytics import RecoveryEvent

class RecoveryAnalytics:
    async def track_sequence_start(self, sequence: RecoverySequence):
        """Track when recovery sequence starts."""
        await RecoveryEvent.create(
            sequence_id=sequence.id,
            event_type="sequence_started",
            cart_value=sequence.cart.total_price,
            timestamp=datetime.utcnow()
        )

    async def track_email_sent(self, sequence: RecoverySequence, step: str):
        """Track email delivery."""
        await RecoveryEvent.create(
            sequence_id=sequence.id,
            event_type="email_sent",
            step=step,
            timestamp=datetime.utcnow()
        )

    async def track_recovery(self, sequence: RecoverySequence, order_value: float):
        """Track successful cart recovery."""
        await RecoveryEvent.create(
            sequence_id=sequence.id,
            event_type="cart_recovered",
            recovered_value=order_value,
            timestamp=datetime.utcnow()
        )

    async def get_recovery_rate(self, store_id: UUID, days: int = 30) -> float:
        """Calculate recovery rate for the last N days."""
        sequences = await RecoverySequence.filter(
            cart__store_id=store_id,
            started_at__gte=datetime.utcnow() - timedelta(days=days)
        )

        total_sequences = len(sequences)
        recovered = len([s for s in sequences if s.stopped_reason == "purchased"])

        return (recovered / total_sequences * 100) if total_sequences > 0 else 0
```

### 2.6 Sequence Management API

**Location:** `apps/api/app/api/v1/recovery.py`

- [ ] Create endpoints to view active sequences
- [ ] Allow manual sequence stopping/starting
- [ ] Provide sequence performance analytics
- [ ] Enable sequence configuration per store

**API endpoints:**

```python
from fastapi import APIRouter, Depends
from app.services.recovery_analytics import RecoveryAnalytics

router = APIRouter(prefix="/recovery", tags=["recovery"])

@router.get("/sequences")
async def get_active_sequences(
    store: Store = Depends(get_current_store)
) -> list[RecoverySequenceResponse]:
    """Get all active recovery sequences for store."""
    sequences = await RecoverySequence.filter(
        cart__store_id=store.id,
        completed_at__isnull=True
    ).prefetch_related("cart")

    return [RecoverySequenceResponse.from_orm(seq) for seq in sequences]

@router.post("/sequences/{sequence_id}/stop")
async def stop_sequence(
    sequence_id: UUID,
    reason: str,
    store: Store = Depends(get_current_store)
) -> dict:
    """Manually stop a recovery sequence."""
    sequence = await RecoverySequence.get(sequence_id)
    if sequence.cart.store_id != store.id:
        raise HTTPException(status_code=404)

    await stop_recovery_sequence(sequence_id, reason)
    return {"status": "stopped", "reason": reason}

@router.get("/analytics")
async def get_recovery_analytics(
    days: int = 30,
    store: Store = Depends(get_current_store)
) -> RecoveryAnalyticsResponse:
    """Get recovery performance analytics."""
    analytics = RecoveryAnalytics()

    return RecoveryAnalyticsResponse(
        recovery_rate=await analytics.get_recovery_rate(store.id, days),
        total_sequences=await analytics.get_sequence_count(store.id, days),
        recovered_revenue=await analytics.get_recovered_revenue(store.id, days),
        avg_sequence_length=await analytics.get_avg_sequence_length(store.id, days)
    )
```

---

## Files to Create/Modify

| File                                          | Action | Purpose                            |
| --------------------------------------------- | ------ | ---------------------------------- |
| `app/services/recovery.py`                    | Create | Core recovery sequence engine      |
| `app/services/recovery_messages.py`           | Create | AI message generation              |
| `app/services/customer_segmentation.py`       | Create | Customer analysis and segmentation |
| `app/services/recovery_analytics.py`          | Create | Performance tracking               |
| `app/workers/recovery_tasks.py`               | Create | Celery tasks for sequences         |
| `app/api/v1/recovery.py`                      | Create | Recovery management endpoints      |
| `app/models/recovery.py`                      | Create | RecoverySequence model             |
| `app/models/analytics.py`                     | Create | RecoveryEvent model                |
| `app/schemas/recovery.py`                     | Create | Pydantic schemas                   |
| `alembic/versions/xxx_add_recovery_tables.py` | Create | Database migration                 |

---

## Dependencies

```toml
# Add to pyproject.toml
openai = "^1.0"         # AI message generation
celery = "^5.3"         # Task scheduling
redis = "^5.0"          # Celery broker
jinja2 = "^3.1"         # Email templates
```

---

## Testing

- [ ] Unit test: sequence progression logic
- [ ] Unit test: AI message generation quality
- [ ] Unit test: customer segmentation accuracy
- [ ] Integration test: full sequence execution
- [ ] Test: sequence interruption on purchase
- [ ] Test: task retry on failures
- [ ] Test: analytics calculation accuracy

---

## Acceptance Criteria

1. Recovery sequences start automatically after cart abandonment
2. Messages are personalized based on cart contents and customer history
3. Sequences progress through all steps with correct timing
4. Sequences stop immediately when customer purchases
5. Analytics accurately track recovery performance
6. Failed tasks retry with exponential backoff
7. Merchants can view and manage active sequences

---

## Notes

- Start with simple message templates, enhance with AI iteratively
- Monitor task queue performance under high webhook volume
- Consider A/B testing different message tones and timing
- Implement proper error handling for OpenAI API failures
