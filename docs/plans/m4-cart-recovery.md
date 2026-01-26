# Milestone 4: Cart Recovery Agent - Implementation Plan

> **Status:** Not Started  
> **Timeline:** 3 weeks  
> **Goal:** Proactively recover abandoned carts through intelligent, personalized outreach.

---

## Overview

Milestone 4 transforms Reva from a reactive support agent into a proactive revenue driver. With 70% of carts abandoned, recovering just 5-10% represents significant revenue for merchants.

The Cart Recovery Agent uses Shopify webhooks to detect abandonment, analyzes cart contents and customer behavior, then executes multi-touch recovery sequences across email and on-site channels.

### Success Criteria

- [ ] Shopify webhook handlers for cart events
- [ ] Abandonment detection and timing logic
- [ ] AI-powered personalized recovery messages
- [ ] Multi-touch sequence engine (1hr → 24hr → 72hr)
- [ ] Email delivery via Resend integration
- [ ] On-site popup for returning visitors
- [ ] Klaviyo coordination to avoid duplicate messages
- [ ] Recovery analytics and attribution tracking
- [ ] GA4 conversion tracking with UTM parameters

### Success Metrics

| Metric                       | Target      |
| ---------------------------- | ----------- |
| Cart recovery rate           | 5-10%       |
| Email open rate              | > 25%       |
| Click-through rate           | > 5%        |
| Sequence completion rate     | > 80%       |
| Revenue attribution accuracy | > 95%       |
| Webhook processing time      | < 2 seconds |

---

## Implementation Phases

M4 is broken into 3 sequential phases:

| Phase                                                  | Focus                        | Duration | Status      |
| ------------------------------------------------------ | ---------------------------- | -------- | ----------- |
| [Phase 1](m4-phases/phase-1-webhook-detection.md)      | Webhook Handling & Detection | 1 week   | Not Started |
| [Phase 2](m4-phases/phase-2-recovery-engine.md)        | Recovery Engine & Sequences  | 1 week   | Not Started |
| [Phase 3](m4-phases/phase-3-marketing-integrations.md) | Marketing Integrations       | 1 week   | Not Started |

### Why This Order?

1. **Phase 1 (Webhooks)** - Build the event foundation. Must reliably capture cart events.
2. **Phase 2 (Recovery)** - Core recovery logic and timing engine. The main value driver.
3. **Phase 3 (Integrations)** - Marketing tool coordination and advanced tracking.

This order allows for:

- Fastest path to basic recovery functionality
- Testing with simple email sequences before complex integrations
- Marketing coordination as enhancement, not blocker

---

## Architecture

```
Shopify Store              Reva API                Recovery Engine           External Services
     |                        |                         |                         |
     | Webhook: cart_abandoned |                         |                         |
     |----------------------->|                         |                         |
     |                        | analyze_cart()          |                         |
     |                        |------------------------>|                         |
     |                        |                         | determine_strategy()    |
     |                        |                         |------------------------>|
     |                        |                         |                         | Check Klaviyo
     |                        |                         |                         |<------------|
     |                        |                         |<------------------------|             |
     |                        |<------------------------|                         |             |
     |                        | schedule_sequence()     |                         |             |
     |                        |------------------------>|                         |             |
     |                        |                         | Celery: send_email     |             |
     |                        |                         |------------------------>|             |
     |                        |                         |                         | Resend API  |
     |                        |                         |                         |------------>|
     |                        |                         |                         |<------------|
     |                        |                         |<------------------------|             |
     |                        |<------------------------|                         |             |
     |                        |                         |                         |             |
     | Customer returns       |                         |                         |             |
     |<-----------------------|                         |                         |             |
     | Show recovery popup    |                         |                         |             |
```

### Key Components

| Component           | Location                            | Purpose                            |
| ------------------- | ----------------------------------- | ---------------------------------- |
| Webhook Handler     | `app/api/v1/webhooks/shopify.py`    | Process cart abandonment events    |
| Recovery Engine     | `app/services/recovery.py`          | Orchestrate recovery sequences     |
| Message Generator   | `app/services/recovery_messages.py` | AI-powered message personalization |
| Sequence Scheduler  | `app/workers/recovery_tasks.py`     | Time-delayed follow-ups            |
| Email Service       | `app/services/email.py`             | Resend integration                 |
| Klaviyo Integration | `app/integrations/klaviyo.py`       | Check existing email flows         |
| Analytics Tracker   | `app/services/analytics.py`         | GA4 and internal tracking          |

---

## Recovery Sequence Timing

| Timing   | Channel       | Message Type              | Trigger Condition        |
| -------- | ------------- | ------------------------- | ------------------------ |
| 1 hour   | On-site popup | Gentle reminder           | Customer returns to site |
| 2 hours  | Email         | Helpful, answer questions | Email available          |
| 24 hours | Email         | Social proof, reviews     | Previous email opened    |
| 48 hours | Email         | Scarcity (if low stock)   | High-value cart          |
| 72 hours | Email         | Final offer (discount)    | Merchant approval        |

### Shopify Webhook Events

| Webhook            | Purpose                             | Action                 |
| ------------------ | ----------------------------------- | ---------------------- |
| `carts/create`     | New cart started                    | Track cart creation    |
| `carts/update`     | Cart modified (items added/removed) | Update cart analysis   |
| `checkouts/create` | Checkout process started            | Mark as high-intent    |
| `orders/create`    | Purchase completed                  | Stop recovery sequence |

---

## Technical Decisions

| Decision             | Choice               | Rationale                               |
| -------------------- | -------------------- | --------------------------------------- |
| Message Generation   | OpenAI GPT-4o        | Best personalization quality            |
| Email Service        | Resend               | Developer-friendly, good deliverability |
| Sequence Scheduling  | Celery with Redis    | Reliable delayed task execution         |
| Webhook Verification | HMAC SHA256          | Shopify standard, secure                |
| Recovery Attribution | UTM parameters + GA4 | Standard e-commerce tracking            |
| Klaviyo Integration  | REST API polling     | Check for existing recovery flows       |

---

## Dependencies

### External Services

- Shopify webhooks (cart events)
- OpenAI API (message personalization)
- Resend API (email delivery)
- Klaviyo API (coordination)
- Google Analytics 4 (attribution)

### Internal Prerequisites

- M1 complete (chat system, knowledge base)
- M2 complete (conversation management)
- M3 complete (proactive engagement)
- Celery workers configured
- Redis for task queuing

---

## Deliverables Checklist

From [ROADMAP.md](../../ROADMAP.md#milestone-4-cart-recovery-agent):

- [ ] Shopify webhook handlers
- [ ] Recovery sequence engine
- [ ] AI message generation
- [ ] Email integration (Resend)
- [ ] Klaviyo integration (check existing flows)
- [ ] On-site popup for returning visitors
- [ ] Incentive rules engine
- [ ] Recovery analytics dashboard
- [ ] GA4 conversion tracking

---

## Risk Mitigation

| Risk                        | Mitigation                                 |
| --------------------------- | ------------------------------------------ |
| Webhook delivery failures   | Retry logic with exponential backoff       |
| Email deliverability        | Resend reputation, proper SPF/DKIM setup   |
| Duplicate recovery messages | Klaviyo API checks before sending          |
| Customer privacy concerns   | Clear opt-out links, GDPR compliance       |
| High email volume costs     | Smart throttling, merchant spending limits |
| Sequence timing accuracy    | Redis-backed Celery with monitoring        |

---

## References

- [ROADMAP.md - Milestone 4](../../ROADMAP.md#milestone-4-cart-recovery-agent)
- [M3 Proactive Engagement Plan](m3-proactive-engagement.md)
- [Shopify Webhook Documentation](https://shopify.dev/docs/api/webhooks)
- [Resend API Documentation](https://resend.com/docs)
- [Klaviyo API Documentation](https://developers.klaviyo.com/en)
