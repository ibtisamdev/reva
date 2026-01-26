# Phase 1: Analytics Pipeline & Data Model

> **Parent:** [M7 Analytics & Self-Improvement](../m7-analytics.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** M1-M6 complete (conversation data)

---

## Goal

Build the analytics data pipeline that tracks conversation events, calculates key metrics, and stores analytics data for dashboard consumption.

---

## Tasks

### 1.1 Analytics Data Model

**Location:** `apps/api/app/models/analytics.py`

- [ ] Create analytics tables for time-series data
- [ ] Design conversation events schema
- [ ] Create metrics aggregation tables
- [ ] Add indexes for time-based queries

**Database Schema:**

```sql
-- Conversation events (raw data)
CREATE TABLE conversation_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    store_id UUID NOT NULL REFERENCES stores(id),
    event_type VARCHAR(50) NOT NULL, -- 'started', 'message_sent', 'resolved', 'escalated', 'abandoned'
    event_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily metrics (aggregated)
CREATE TABLE daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    date DATE NOT NULL,
    total_conversations INTEGER DEFAULT 0,
    resolved_conversations INTEGER DEFAULT 0,
    escalated_conversations INTEGER DEFAULT 0,
    abandoned_conversations INTEGER DEFAULT 0,
    avg_response_time_ms INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    unique_customers INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(store_id, date)
);

-- Quality scores
CREATE TABLE conversation_quality_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    store_id UUID NOT NULL REFERENCES stores(id),
    overall_score DECIMAL(3,2), -- 0.00 to 1.00
    helpfulness_score DECIMAL(3,2),
    accuracy_score DECIMAL(3,2),
    politeness_score DECIMAL(3,2),
    scored_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Content gaps
CREATE TABLE content_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    topic VARCHAR(255) NOT NULL,
    frequency INTEGER DEFAULT 1,
    confidence_threshold DECIMAL(3,2),
    example_questions TEXT[],
    status VARCHAR(20) DEFAULT 'identified', -- 'identified', 'in_progress', 'resolved'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 1.2 Event Tracking Service

**Location:** `apps/api/app/analytics/events.py`

- [ ] Create async event tracking system
- [ ] Track conversation lifecycle events
- [ ] Track message-level events
- [ ] Implement event batching for performance

**Event Types:**

```python
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional

class EventType(str, Enum):
    CONVERSATION_STARTED = "conversation_started"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    CONVERSATION_RESOLVED = "conversation_resolved"
    CONVERSATION_ESCALATED = "conversation_escalated"
    CONVERSATION_ABANDONED = "conversation_abandoned"
    KNOWLEDGE_RETRIEVED = "knowledge_retrieved"
    CITATION_CLICKED = "citation_clicked"

class AnalyticsEvent(BaseModel):
    conversation_id: UUID
    store_id: UUID
    event_type: EventType
    event_data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

async def track_event(event: AnalyticsEvent) -> None:
    """Track an analytics event asynchronously."""
    # Implementation with batching and async insert
    pass

async def track_conversation_started(
    conversation_id: UUID,
    store_id: UUID,
    customer_context: Optional[Dict[str, Any]] = None
) -> None:
    """Track when a conversation starts."""
    await track_event(AnalyticsEvent(
        conversation_id=conversation_id,
        store_id=store_id,
        event_type=EventType.CONVERSATION_STARTED,
        event_data=customer_context or {}
    ))
```

### 1.3 Metrics Calculation Engine

**Location:** `apps/api/app/analytics/metrics.py`

- [ ] Calculate daily/weekly/monthly aggregations
- [ ] Compute resolution rates and response times
- [ ] Calculate customer satisfaction metrics
- [ ] Implement real-time metric updates

**Key Metrics:**

```python
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

@dataclass
class ConversationMetrics:
    total_conversations: int
    resolved_conversations: int
    escalated_conversations: int
    abandoned_conversations: int
    resolution_rate: float
    escalation_rate: float
    abandonment_rate: float
    avg_response_time_ms: int
    avg_conversation_length: int
    unique_customers: int

@dataclass
class PeriodMetrics:
    date_range: tuple[date, date]
    metrics: ConversationMetrics
    previous_period: Optional[ConversationMetrics] = None

    @property
    def growth_rate(self) -> Optional[float]:
        if not self.previous_period:
            return None
        if self.previous_period.total_conversations == 0:
            return 1.0 if self.metrics.total_conversations > 0 else 0.0
        return (self.metrics.total_conversations - self.previous_period.total_conversations) / self.previous_period.total_conversations

async def calculate_daily_metrics(store_id: UUID, target_date: date) -> ConversationMetrics:
    """Calculate metrics for a specific day."""
    pass

async def calculate_period_metrics(
    store_id: UUID,
    start_date: date,
    end_date: date,
    include_comparison: bool = True
) -> PeriodMetrics:
    """Calculate metrics for a date range with optional comparison to previous period."""
    pass
```

### 1.4 Analytics Service Layer

**Location:** `apps/api/app/services/analytics.py`

- [ ] Business logic for analytics operations
- [ ] ROI calculation algorithms
- [ ] Cost savings estimation
- [ ] Performance trend analysis

**ROI Calculator:**

```python
@dataclass
class ROICalculation:
    total_conversations: int
    ai_resolved_conversations: int
    avg_human_agent_cost_per_hour: float = 25.0  # Configurable
    avg_conversation_time_minutes: float = 8.0   # Configurable
    ai_cost_per_conversation: float = 0.05       # Configurable

    @property
    def human_agent_cost(self) -> float:
        """Cost if all conversations were handled by humans."""
        total_hours = (self.total_conversations * self.avg_conversation_time_minutes) / 60
        return total_hours * self.avg_human_agent_cost_per_hour

    @property
    def ai_cost(self) -> float:
        """Actual cost with AI handling."""
        return self.total_conversations * self.ai_cost_per_conversation

    @property
    def savings(self) -> float:
        """Total cost savings from AI."""
        human_cost_for_ai_conversations = (
            self.ai_resolved_conversations *
            self.avg_conversation_time_minutes / 60 *
            self.avg_human_agent_cost_per_hour
        )
        ai_cost_for_resolved = self.ai_resolved_conversations * self.ai_cost_per_conversation
        return human_cost_for_ai_conversations - ai_cost_for_resolved

    @property
    def roi_percentage(self) -> float:
        """ROI as a percentage."""
        if self.ai_cost == 0:
            return 0.0
        return (self.savings / self.ai_cost) * 100

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_metrics(
        self,
        store_id: UUID,
        period: str = "month"
    ) -> Dict[str, Any]:
        """Get key metrics for dashboard display."""
        pass

    async def calculate_roi(
        self,
        store_id: UUID,
        period_days: int = 30
    ) -> ROICalculation:
        """Calculate ROI for a given period."""
        pass
```

### 1.5 Analytics API Endpoints

**Location:** `apps/api/app/api/v1/analytics.py`

- [ ] Dashboard metrics endpoint
- [ ] Historical data endpoint
- [ ] ROI calculation endpoint
- [ ] Export data endpoint

**API Endpoints:**

```python
from fastapi import APIRouter, Depends, Query
from datetime import date, datetime
from typing import Optional

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/dashboard")
async def get_dashboard_metrics(
    period: str = Query("month", regex="^(day|week|month|quarter|year)$"),
    store: Store = Depends(get_current_store),
    analytics_service: AnalyticsService = Depends()
) -> Dict[str, Any]:
    """Get key metrics for the analytics dashboard."""
    return await analytics_service.get_dashboard_metrics(store.id, period)

@router.get("/conversations/trends")
async def get_conversation_trends(
    start_date: date = Query(...),
    end_date: date = Query(...),
    granularity: str = Query("day", regex="^(hour|day|week|month)$"),
    store: Store = Depends(get_current_store),
    analytics_service: AnalyticsService = Depends()
) -> List[Dict[str, Any]]:
    """Get conversation trends over time."""
    pass

@router.get("/roi")
async def calculate_roi(
    period_days: int = Query(30, ge=1, le=365),
    store: Store = Depends(get_current_store),
    analytics_service: AnalyticsService = Depends()
) -> ROICalculation:
    """Calculate ROI for the specified period."""
    return await analytics_service.calculate_roi(store.id, period_days)

@router.get("/export")
async def export_analytics_data(
    start_date: date = Query(...),
    end_date: date = Query(...),
    format: str = Query("csv", regex="^(csv|json)$"),
    store: Store = Depends(get_current_store)
) -> StreamingResponse:
    """Export analytics data in CSV or JSON format."""
    pass
```

### 1.6 Background Processing

**Location:** `apps/api/app/workers/analytics_tasks.py`

- [ ] Daily metrics aggregation task
- [ ] Weekly/monthly rollup tasks
- [ ] Data cleanup and archiving
- [ ] Metric recalculation for historical data

**Celery Tasks:**

```python
from celery import Celery
from datetime import date, timedelta

@celery.task
async def calculate_daily_metrics_task(target_date: str = None):
    """Calculate daily metrics for all stores."""
    if target_date:
        date_obj = date.fromisoformat(target_date)
    else:
        date_obj = date.today() - timedelta(days=1)

    # Process all stores
    async with get_db_session() as db:
        stores = await db.execute(select(Store))
        for store in stores.scalars():
            await calculate_daily_metrics(store.id, date_obj)

@celery.task
async def cleanup_old_events_task():
    """Clean up old analytics events (keep last 90 days)."""
    cutoff_date = datetime.utcnow() - timedelta(days=90)
    async with get_db_session() as db:
        await db.execute(
            delete(ConversationEvent).where(
                ConversationEvent.created_at < cutoff_date
            )
        )
        await db.commit()
```

---

## Files to Create/Modify

| File                                | Action | Purpose                       |
| ----------------------------------- | ------ | ----------------------------- |
| `app/models/analytics.py`           | Create | Analytics data models         |
| `app/analytics/__init__.py`         | Create | Package init                  |
| `app/analytics/events.py`           | Create | Event tracking system         |
| `app/analytics/metrics.py`          | Create | Metrics calculation           |
| `app/services/analytics.py`         | Create | Analytics business logic      |
| `app/api/v1/analytics.py`           | Create | Analytics API endpoints       |
| `app/schemas/analytics.py`          | Create | Pydantic models for analytics |
| `app/workers/analytics_tasks.py`    | Create | Background processing tasks   |
| `app/core/events.py`                | Create | Event system integration      |
| `alembic/versions/xxx_analytics.py` | Create | Database migration            |

---

## Dependencies

```toml
# Add to pyproject.toml
pandas = "^2.0"           # Data analysis
numpy = "^1.24"           # Numerical computations
```

---

## Testing

- [ ] Unit test: event tracking stores events correctly
- [ ] Unit test: metrics calculation produces accurate results
- [ ] Unit test: ROI calculation matches expected values
- [ ] Integration test: full analytics pipeline (event -> metrics -> API)
- [ ] Performance test: analytics queries under load
- [ ] Test: data retention and cleanup

---

## Acceptance Criteria

1. All conversation events are tracked automatically
2. Daily metrics are calculated and stored correctly
3. Dashboard API returns metrics within 2 seconds
4. ROI calculations are accurate and configurable
5. Analytics data is properly scoped by store (multi-tenant)
6. Background tasks run reliably without blocking main app

---

## Notes

- Start with basic metrics, add advanced analytics iteratively
- Consider using TimescaleDB extension for better time-series performance
- Implement proper data retention policies from the start
- Add monitoring for analytics pipeline health
