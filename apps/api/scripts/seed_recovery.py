"""Seed script for M4 Cart Recovery testing.

Creates test data for all recovery testing phases:
- 2 stores (primary + cross-tenant)
- 1 store integration (Shopify)
- 5 abandoned checkouts in different states
- 1 active recovery sequence (mid-progress)
- Recovery events for analytics
- 1 conversation (for widget check)
- 1 email unsubscribe record

Usage:
    cd apps/api && uv run python -m scripts.seed_recovery
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.abandoned_checkout import AbandonedCheckout, CheckoutStatus
from app.models.conversation import Channel, Conversation, ConversationStatus
from app.models.email_unsubscribe import EmailUnsubscribe
from app.models.integration import IntegrationStatus, PlatformType, StoreIntegration
from app.models.recovery_event import RecoveryEvent
from app.models.recovery_sequence import RecoverySequence, SequenceStatus
from app.models.store import Store

# Fixed UUIDs for easy reference
STORE_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
OTHER_STORE_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002")
ORG_ID = "test-org-seed"
OTHER_ORG_ID = "other-org-seed"

# Checkout UUIDs
AC1_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001")  # alice - stale active
AC2_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")  # bob - fresh active
AC3_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000003")  # carol - abandoned, has sequence
AC4_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000004")  # dave - completed
AC5_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000005")  # eve - low value active

# Sequence / event UUIDs
SEQ_CAROL_ID = uuid.UUID("cccccccc-0000-0000-0000-000000000001")
EVENT1_ID = uuid.UUID("dddddddd-0000-0000-0000-000000000001")
EVENT2_ID = uuid.UUID("dddddddd-0000-0000-0000-000000000002")
EVENT3_ID = uuid.UUID("dddddddd-0000-0000-0000-000000000003")

# Conversation UUID
CONV_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000001")

SAMPLE_LINE_ITEMS = [
    {
        "title": "Premium Widget",
        "quantity": 2,
        "price": "49.99",
        "variant_title": "Blue / Large",
        "image_url": "https://placehold.co/64x64/4F46E5/white?text=PW",
    },
    {
        "title": "Widget Case",
        "quantity": 1,
        "price": "30.01",
        "variant_title": "Black",
        "image_url": "https://placehold.co/64x64/059669/white?text=WC",
    },
]

LOW_VALUE_ITEMS = [
    {
        "title": "Sticker Pack",
        "quantity": 1,
        "price": "5.00",
        "image_url": None,
    },
    {
        "title": "Mini Widget",
        "quantity": 1,
        "price": "10.00",
        "image_url": None,
    },
]


async def seed(session: AsyncSession) -> None:
    now = datetime.now(UTC)

    # ── Cleanup existing seed data ──────────────────────────────────────
    # Delete in reverse dependency order
    for table in [
        "recovery_events",
        "recovery_sequences",
        "email_unsubscribes",
        "abandoned_checkouts",
        "conversations",
        "store_integrations",
    ]:
        await session.execute(
            text(f"DELETE FROM {table} WHERE store_id IN (:s1, :s2)"),
            {"s1": str(STORE_ID), "s2": str(OTHER_STORE_ID)},
        )
    await session.execute(
        text("DELETE FROM stores WHERE id IN (:s1, :s2)"),
        {"s1": str(STORE_ID), "s2": str(OTHER_STORE_ID)},
    )
    await session.flush()

    # ── Store 1 (primary test store) ────────────────────────────────────
    store = Store(
        id=STORE_ID,
        organization_id=ORG_ID,
        name="Test Recovery Store",
        email="store@test-recovery.com",
        plan="pro",
        is_active=True,
        settings={
            "recovery": {
                "enabled": True,
                "abandonment_threshold_minutes": 5,
                "min_cart_value": 0,
                "sequence_timing_minutes": [1, 2, 3, 5],
                "discount_enabled": False,
                "discount_percent": 10,
                "max_emails_per_day": 50,
                "exclude_email_patterns": [],
            },
        },
    )
    session.add(store)

    # ── Store 2 (cross-tenant testing) ──────────────────────────────────
    other_store = Store(
        id=OTHER_STORE_ID,
        organization_id=OTHER_ORG_ID,
        name="Other Store",
        email="other@test.com",
        plan="free",
        is_active=True,
        settings={},
    )
    session.add(other_store)
    await session.flush()

    # ── Store Integration (Shopify) ─────────────────────────────────────
    integration = StoreIntegration(
        store_id=STORE_ID,
        platform=PlatformType.SHOPIFY,
        platform_store_id="test-recovery.myshopify.com",
        platform_domain="test-recovery.myshopify.com",
        credentials={},
        status=IntegrationStatus.ACTIVE,
    )
    session.add(integration)

    # ── AC-1: Alice — stale active (should be detected as abandoned) ────
    ac1 = AbandonedCheckout(
        id=AC1_ID,
        store_id=STORE_ID,
        shopify_checkout_id="seed_chk_001",
        shopify_checkout_token="tok_seed_001",
        customer_email="alice@test.com",
        customer_name="Alice Seed",
        total_price=129.99,
        currency="USD",
        line_items=SAMPLE_LINE_ITEMS,
        checkout_url="https://test-recovery.myshopify.com/checkouts/seed_chk_001",
        status=CheckoutStatus.ACTIVE,
    )
    session.add(ac1)

    # ── AC-2: Bob — fresh active (too recent, should NOT be detected) ───
    ac2 = AbandonedCheckout(
        id=AC2_ID,
        store_id=STORE_ID,
        shopify_checkout_id="seed_chk_002",
        shopify_checkout_token="tok_seed_002",
        customer_email="bob@test.com",
        customer_name="Bob Seed",
        total_price=49.99,
        currency="USD",
        line_items=SAMPLE_LINE_ITEMS[:1],
        checkout_url="https://test-recovery.myshopify.com/checkouts/seed_chk_002",
        status=CheckoutStatus.ACTIVE,
    )
    session.add(ac2)

    # ── AC-3: Carol — abandoned, has active recovery sequence ───────────
    ac3 = AbandonedCheckout(
        id=AC3_ID,
        store_id=STORE_ID,
        shopify_checkout_id="seed_chk_003",
        shopify_checkout_token="tok_seed_003",
        customer_email="carol@test.com",
        customer_name="Carol Seed",
        total_price=89.50,
        currency="USD",
        line_items=SAMPLE_LINE_ITEMS,
        checkout_url="https://test-recovery.myshopify.com/checkouts/seed_chk_003",
        status=CheckoutStatus.ABANDONED,
        abandonment_detected_at=now - timedelta(hours=3),
    )
    session.add(ac3)

    # ── AC-4: Dave — completed (order placed) ───────────────────────────
    ac4 = AbandonedCheckout(
        id=AC4_ID,
        store_id=STORE_ID,
        shopify_checkout_id="seed_chk_004",
        shopify_checkout_token="tok_seed_004",
        customer_email="dave@test.com",
        customer_name="Dave Seed",
        total_price=200.00,
        currency="USD",
        line_items=SAMPLE_LINE_ITEMS,
        checkout_url="https://test-recovery.myshopify.com/checkouts/seed_chk_004",
        status=CheckoutStatus.COMPLETED,
        abandonment_detected_at=now - timedelta(days=2),
        recovered_at=now - timedelta(days=1),
        completed_order_id="order_99001",
    )
    session.add(ac4)

    # ── AC-5: Eve — low value active (for min_cart_value testing) ───────
    ac5 = AbandonedCheckout(
        id=AC5_ID,
        store_id=STORE_ID,
        shopify_checkout_id="seed_chk_005",
        shopify_checkout_token="tok_seed_005",
        customer_email="eve@test.com",
        customer_name="Eve Seed",
        total_price=15.00,
        currency="USD",
        line_items=LOW_VALUE_ITEMS,
        checkout_url="https://test-recovery.myshopify.com/checkouts/seed_chk_005",
        status=CheckoutStatus.ACTIVE,
    )
    session.add(ac5)
    await session.flush()

    # Backdate AC-1 and AC-5 to be stale (2 hours ago)
    await session.execute(
        text("UPDATE abandoned_checkouts SET updated_at = :ts WHERE id IN (:id1, :id5)"),
        {
            "ts": now - timedelta(hours=2),
            "id1": str(AC1_ID),
            "id5": str(AC5_ID),
        },
    )
    # Keep AC-2 fresh (30 seconds ago)
    await session.execute(
        text("UPDATE abandoned_checkouts SET updated_at = :ts WHERE id = :id2"),
        {"ts": now - timedelta(seconds=30), "id2": str(AC2_ID)},
    )

    # ── Recovery Sequence for Carol (mid-progress) ──────────────────────
    seq = RecoverySequence(
        id=SEQ_CAROL_ID,
        store_id=STORE_ID,
        abandoned_checkout_id=AC3_ID,
        customer_email="carol@test.com",
        sequence_type="first_time",
        status=SequenceStatus.ACTIVE,
        current_step_index=1,
        steps_completed=[
            {
                "step_index": 0,
                "sent_at": (now - timedelta(hours=2)).isoformat(),
                "subject": "Did you forget something?",
                "email_id": "seed_email_001",
            },
        ],
        started_at=now - timedelta(hours=3),
        next_step_at=now + timedelta(hours=1),
    )
    session.add(seq)
    await session.flush()

    # ── Recovery Events ─────────────────────────────────────────────────
    event1 = RecoveryEvent(
        id=EVENT1_ID,
        store_id=STORE_ID,
        sequence_id=SEQ_CAROL_ID,
        abandoned_checkout_id=AC3_ID,
        event_type="sequence_started",
        channel="email",
        metadata_={},
    )
    event2 = RecoveryEvent(
        id=EVENT2_ID,
        store_id=STORE_ID,
        sequence_id=SEQ_CAROL_ID,
        abandoned_checkout_id=AC3_ID,
        event_type="email_sent",
        step_index=0,
        channel="email",
        metadata_={"subject": "Did you forget something?", "email_id": "seed_email_001"},
    )
    # Add a completed-checkout event for dave (for analytics)
    event3 = RecoveryEvent(
        id=EVENT3_ID,
        store_id=STORE_ID,
        abandoned_checkout_id=AC4_ID,
        event_type="sequence_completed",
        channel="email",
        metadata_={},
    )
    session.add_all([event1, event2, event3])

    # ── Conversation (for widget recovery check) ────────────────────────
    conv = Conversation(
        id=CONV_ID,
        store_id=STORE_ID,
        session_id="test-widget-session-abc",
        customer_email="carol@test.com",
        customer_name="Carol Seed",
        channel=Channel.WIDGET,
        status=ConversationStatus.ACTIVE,
    )
    session.add(conv)

    # ── Email Unsubscribe (for skip testing) ────────────────────────────
    unsub = EmailUnsubscribe(
        store_id=STORE_ID,
        email="unsub@test.com",
    )
    session.add(unsub)

    await session.commit()


async def main() -> None:
    async with async_session_maker() as session:
        await seed(session)

    print("=" * 60)
    print("  Recovery seed data created successfully!")
    print("=" * 60)
    print()
    print(f"  Store ID (primary):  {STORE_ID}")
    print(f"  Store ID (other):    {OTHER_STORE_ID}")
    print(f"  Org ID (primary):    {ORG_ID}")
    print(f"  Org ID (other):      {OTHER_ORG_ID}")
    print()
    print("  Abandoned Checkouts:")
    print(f"    AC-1 (alice, stale active):  {AC1_ID}")
    print(f"    AC-2 (bob, fresh active):    {AC2_ID}")
    print(f"    AC-3 (carol, abandoned):     {AC3_ID}")
    print(f"    AC-4 (dave, completed):      {AC4_ID}")
    print(f"    AC-5 (eve, low value):       {AC5_ID}")
    print()
    print(f"  Carol's sequence:    {SEQ_CAROL_ID}")
    print(f"  Conversation:        {CONV_ID}")
    print("  Widget session_id:   test-widget-session-abc")
    print("  Unsubscribed email:  unsub@test.com")
    print()
    print("  Recovery settings: enabled=True, threshold=5min, timing=[1,2,3,5]min")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
