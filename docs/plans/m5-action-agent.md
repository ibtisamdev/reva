# Milestone 5: Full Action Agent - Implementation Plan

> **Status:** Not Started  
> **Timeline:** 4 weeks  
> **Goal:** Handle complete support lifecycle with real actions — cancellations, returns, refunds, modifications.

---

## Overview

Milestone 5 delivers **true automation** with 60%+ resolution rates vs 30% for Q&A-only bots. The action agent can perform real customer service tasks like canceling orders, processing refunds, and initiating returns with proper permission controls and human-in-the-loop confirmation.

### Success Criteria

- [ ] Merchant can configure action permissions and limits
- [ ] Agent can cancel unfulfilled orders with confirmation
- [ ] Agent can process refunds up to configured limits
- [ ] Agent can initiate returns with proper validation
- [ ] Agent can apply discounts within merchant-set limits
- [ ] All actions require explicit customer confirmation
- [ ] Complete audit trail for all actions taken
- [ ] Escalation to human agents when needed
- [ ] LangGraph checkpointing for stateful conversations

### Success Metrics

| Metric                     | Target       |
| -------------------------- | ------------ |
| Action success rate        | > 95%        |
| False positive actions     | < 1%         |
| Customer confirmation rate | > 80%        |
| Escalation rate            | < 15%        |
| Action completion time     | < 30 seconds |
| Audit log completeness     | 100%         |

---

## Implementation Phases

M5 is broken into 4 sequential phases:

| Phase                                             | Focus                        | Duration  | Status      |
| ------------------------------------------------- | ---------------------------- | --------- | ----------- |
| [Phase 1](m5-phases/phase-1-permission-system.md) | Permission System & Settings | 1 week    | Not Started |
| [Phase 2](m5-phases/phase-2-action-tools.md)      | Core Action Tools            | 1.5 weeks | Not Started |
| [Phase 3](m5-phases/phase-3-confirmation-flow.md) | Confirmation & Checkpointing | 1 week    | Not Started |
| [Phase 4](m5-phases/phase-4-audit-escalation.md)  | Audit Logging & Escalation   | 0.5 weeks | Not Started |

### Why This Order?

1. **Phase 1 (Permissions)** - Build the safety controls first. No actions without proper permissions.
2. **Phase 2 (Tools)** - Implement the core action tools with Shopify API integration.
3. **Phase 3 (Confirmation)** - Add human-in-the-loop confirmation with LangGraph checkpointing.
4. **Phase 4 (Audit)** - Complete the system with logging and escalation flows.

This order ensures:

- Safety first: permissions prevent unauthorized actions
- Core functionality before advanced features
- Stateful conversations with proper checkpointing
- Complete audit trail for compliance

---

## Architecture

```
Widget/Dashboard         API                    LangGraph Agent           Shopify API
      |                   |                          |                        |
      | POST /chat/action |                          |                        |
      |------------------>|                          |                        |
      |                   | classify_intent()        |                        |
      |                   |------------------------->|                        |
      |                   |                          | check_permissions()    |
      |                   |                          |----------------------->|
      |                   |                          |<-----------------------|
      |                   |                          | request_confirmation() |
      |                   |<-------------------------|                        |
      |<------------------|                          |                        |
      |                   |                          |                        |
      | POST /chat/confirm|                          |                        |
      |------------------>|                          |                        |
      |                   | resume_from_checkpoint() |                        |
      |                   |------------------------->|                        |
      |                   |                          | execute_action()       |
      |                   |                          |----------------------->|
      |                   |                          |<-----------------------|
      |                   |                          | log_audit_trail()      |
      |                   |<-------------------------|                        |
      |<------------------|                          |                        |
```

### LangGraph Action Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                         ACTION GRAPH                                   │
│                                                                        │
│  START ──▶ CLASSIFY ──▶ CHECK PERMISSION                              │
│                              │                                         │
│              ┌───────────────┼───────────────┐                        │
│              ▼               ▼               ▼                        │
│        ┌──────────┐   ┌──────────┐   ┌──────────┐                    │
│        │ ALLOWED  │   │ CONFIRM  │   │ DISABLED │                    │
│        │   AUTO   │   │ REQUIRED │   │  ACTION  │                    │
│        └────┬─────┘   └────┬─────┘   └────┬─────┘                    │
│             │              ▼              │                           │
│             │      ┌──────────────┐       │                           │
│             │      │   REQUEST    │       │                           │
│             │      │ CONFIRMATION │       │                           │
│             │      └──────┬───────┘       │                           │
│             │              ▼              │                           │
│             │      ┌──────────────┐       │                           │
│             │      │ WAIT (chkpt) │       │                           │
│             │      └──────┬───────┘       │                           │
│             │        confirmed?           │                           │
│             │         │    │              │                           │
│             │        YES   NO             │                           │
│             ▼         ▼    ▼              ▼                           │
│        ┌──────────────────────────┐  ┌─────────┐                     │
│        │      EXECUTE ACTION      │  │ EXPLAIN │                     │
│        └────────────┬─────────────┘  │ HANDOFF │                     │
│                     ▼                └────┬────┘                     │
│        ┌──────────────────────────┐       │                          │
│        │      LOG & RESPOND       │◀──────┘                          │
│        └──────────────────────────┘                                  │
└────────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component            | Location                       | Purpose                            |
| -------------------- | ------------------------------ | ---------------------------------- |
| Permission Manager   | `app/services/permissions.py`  | Check action permissions & limits  |
| Action Tools         | `app/agents/tools/`            | Shopify API action implementations |
| LangGraph Agent      | `app/agents/action_agent.py`   | Orchestrate action flow            |
| Confirmation Service | `app/services/confirmation.py` | Handle human-in-the-loop flow      |
| Audit Logger         | `app/services/audit.py`        | Log all actions and decisions      |
| Action API           | `app/api/v1/actions.py`        | HTTP endpoints for actions         |

---

## Technical Decisions

| Decision           | Choice                   | Rationale                                 |
| ------------------ | ------------------------ | ----------------------------------------- |
| Agent Framework    | LangGraph                | Built-in checkpointing, human-in-the-loop |
| Action Permissions | Database-driven          | Flexible per-merchant configuration       |
| Confirmation Flow  | Checkpoint + Resume      | Stateful conversations across requests    |
| Audit Storage      | PostgreSQL               | ACID compliance for audit trail           |
| Action Limits      | Per-action configuration | Granular control over automation scope    |

---

## Dependencies

### External Services

- Shopify Admin API (orders, refunds, cancellations)
- LangGraph (agent orchestration)
- OpenAI API (intent classification)

### Internal Prerequisites

- M1-M4 complete (chat system, knowledge base, analytics)
- Shopify OAuth integration
- Database with audit tables

---

## Deliverables Checklist

From [ROADMAP.md](../../ROADMAP.md#milestone-5-full-action-agent):

- [ ] Action permission system
- [ ] Confirmation flow with checkpointing
- [ ] Order cancellation tool
- [ ] Refund processing tool
- [ ] Return initiation tool
- [ ] Complete audit logging
- [ ] Escalation to human flow

### Actions Available

| Action                     | Complexity | Confirmation | Shopify API Endpoint            |
| -------------------------- | ---------- | ------------ | ------------------------------- |
| Look up order status       | Low        | No           | `GET /orders/{id}.json`         |
| Send tracking link         | Low        | No           | `GET /orders/{id}.json`         |
| Update shipping address    | Medium     | Yes          | `PUT /orders/{id}.json`         |
| Cancel order (pre-fulfill) | Medium     | Yes          | `POST /orders/{id}/cancel.json` |
| Initiate return            | Medium     | Yes          | `POST /orders/{id}/refund.json` |
| Process refund             | High       | Yes          | `POST /orders/{id}/refund.json` |
| Apply discount to order    | Medium     | Yes          | `PUT /orders/{id}.json`         |

---

## Risk Mitigation

| Risk                 | Mitigation                                       |
| -------------------- | ------------------------------------------------ |
| Unauthorized actions | Multi-layer permission checks, audit logging     |
| API failures         | Retry logic, graceful degradation, error logging |
| Customer confusion   | Clear confirmation messages, undo capabilities   |
| Merchant liability   | Configurable limits, explicit opt-in required    |
| State management     | LangGraph checkpointing, database persistence    |
| Shopify rate limits  | Request queuing, exponential backoff             |

---

## References

- [ROADMAP.md - Milestone 5](../../ROADMAP.md#milestone-5-full-action-agent)
- [Shopify Admin API - Orders](https://shopify.dev/docs/api/admin-rest/2024-01/resources/order)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Human-in-the-Loop Patterns](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
