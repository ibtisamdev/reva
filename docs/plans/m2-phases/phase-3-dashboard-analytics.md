# Phase 3: WISMO Dashboard & Analytics

> **Parent:** [M2 Order Status Agent](../m2-order-status.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 1 & 2 complete (verification, tracking integration)

---

## Goal

Build a comprehensive WISMO (Where Is My Order) analytics dashboard for merchants to understand order inquiry patterns, track customer satisfaction, and optimize their fulfillment process.

---

## Tasks

### 3.1 WISMO Analytics Service

**Location:** `apps/api/app/services/analytics.py`

- [ ] Create analytics data aggregation service
- [ ] Track order inquiry patterns and frequency
- [ ] Calculate customer satisfaction metrics
- [ ] Generate fulfillment performance insights
- [ ] Support date range filtering and segmentation

**Analytics Service:**

```python
class WISMOAnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_inquiry_metrics(
        self,
        store_id: UUID,
        date_range: DateRange
    ) -> InquiryMetrics:
        """Get order inquiry statistics."""
        # 1. Count total order inquiries
        # 2. Group by order status
        # 3. Calculate inquiry rate vs total orders
        # 4. Track repeat inquiries

    async def get_fulfillment_insights(
        self,
        store_id: UUID,
        date_range: DateRange
    ) -> FulfillmentInsights:
        """Analyze fulfillment performance."""
        # 1. Average time to ship
        # 2. Delivery performance by carrier
        # 3. Exception rates
        # 4. Customer satisfaction scores
```

### 3.2 Order Inquiry Tracking

**Location:** `apps/api/app/models/analytics.py`

- [ ] Create models to track order inquiries
- [ ] Record inquiry types and resolution status
- [ ] Track customer satisfaction feedback
- [ ] Link inquiries to specific orders and conversations

**Database Schema:**

```sql
-- Order inquiry tracking
CREATE TABLE order_inquiries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    conversation_id UUID REFERENCES conversations(id),
    order_number VARCHAR(100),
    inquiry_type VARCHAR(50), -- 'status', 'tracking', 'delivery', 'refund'
    order_status VARCHAR(50), -- Order status at time of inquiry
    resolved BOOLEAN DEFAULT FALSE,
    resolution_time INTERVAL,
    customer_satisfied BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- WISMO metrics aggregation
CREATE TABLE wismo_daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    date DATE NOT NULL,
    total_orders INTEGER DEFAULT 0,
    total_inquiries INTEGER DEFAULT 0,
    inquiry_rate DECIMAL(5,4), -- inquiries / orders
    avg_resolution_time INTERVAL,
    satisfaction_score DECIMAL(3,2), -- 0-5 scale
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(store_id, date)
);

-- Indexes for analytics queries
CREATE INDEX idx_order_inquiries_store_date ON order_inquiries(store_id, created_at);
CREATE INDEX idx_wismo_metrics_store_date ON wismo_daily_metrics(store_id, date);
```

### 3.3 Dashboard API Endpoints

**Location:** `apps/api/app/api/v1/analytics.py`

- [ ] Create analytics endpoints for dashboard consumption
- [ ] Support various time ranges (7d, 30d, 90d, custom)
- [ ] Provide data in chart-friendly formats
- [ ] Include comparison with previous periods

**Analytics Endpoints:**

```python
@router.get("/wismo/overview")
async def get_wismo_overview(
    store_id: UUID = Depends(get_current_store),
    date_range: str = Query("30d"),
    db: AsyncSession = Depends(get_db)
) -> WISMOOverview:
    """Get high-level WISMO metrics."""

@router.get("/wismo/inquiries")
async def get_inquiry_trends(
    store_id: UUID = Depends(get_current_store),
    date_range: str = Query("30d"),
    group_by: str = Query("day"),
    db: AsyncSession = Depends(get_db)
) -> InquiryTrends:
    """Get inquiry volume trends over time."""

@router.get("/wismo/fulfillment")
async def get_fulfillment_metrics(
    store_id: UUID = Depends(get_current_store),
    date_range: str = Query("30d"),
    db: AsyncSession = Depends(get_db)
) -> FulfillmentMetrics:
    """Get fulfillment performance metrics."""
```

### 3.4 Dashboard UI Components

**Location:** `apps/web/src/components/analytics/`

- [ ] Create WISMO dashboard page layout
- [ ] Build inquiry volume charts (line, bar charts)
- [ ] Create fulfillment performance widgets
- [ ] Add order status distribution pie chart
- [ ] Implement date range selector component

**Dashboard Components:**

```typescript
// WISMO Overview Component
export function WISMOOverview({ storeId, dateRange }: WISMOOverviewProps) {
  const { data: metrics } = useWISMOMetrics(storeId, dateRange);

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
      <MetricCard
        title="Total Inquiries"
        value={metrics?.totalInquiries}
        change={metrics?.inquiryChange}
      />
      <MetricCard
        title="Inquiry Rate"
        value={`${metrics?.inquiryRate}%`}
        change={metrics?.rateChange}
      />
      <MetricCard
        title="Avg Resolution Time"
        value={metrics?.avgResolutionTime}
        change={metrics?.resolutionChange}
      />
      <MetricCard
        title="Satisfaction Score"
        value={metrics?.satisfactionScore}
        change={metrics?.satisfactionChange}
      />
    </div>
  );
}

// Inquiry Trends Chart
export function InquiryTrendsChart({ data }: InquiryTrendsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Order Inquiry Trends</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="inquiries" stroke="#8884d8" />
            <Line type="monotone" dataKey="orders" stroke="#82ca9d" />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

### 3.5 Order Timeline Visualization

**Location:** `apps/web/src/components/orders/OrderTimeline.tsx`

- [ ] Create interactive order timeline component
- [ ] Show order journey from purchase to delivery
- [ ] Include tracking events and status updates
- [ ] Support customer inquiry annotations
- [ ] Add estimated vs actual delivery comparisons

**Order Timeline Component:**

```typescript
interface TimelineEvent {
  id: string;
  timestamp: Date;
  type: 'order' | 'fulfillment' | 'tracking' | 'inquiry' | 'delivery';
  title: string;
  description: string;
  location?: string;
  status: 'completed' | 'in_progress' | 'pending' | 'exception';
}

export function OrderTimeline({ orderNumber }: OrderTimelineProps) {
  const { data: events } = useOrderTimeline(orderNumber);

  return (
    <div className="space-y-4">
      {events?.map((event) => (
        <TimelineItem
          key={event.id}
          event={event}
          isLast={event === events[events.length - 1]}
        />
      ))}
    </div>
  );
}
```

### 3.6 Automated Insights Generation

**Location:** `apps/api/app/services/insights.py`

- [ ] Generate automated insights from WISMO data
- [ ] Identify patterns in order inquiries
- [ ] Suggest fulfillment process improvements
- [ ] Alert on unusual inquiry spikes
- [ ] Provide actionable recommendations

**Insights Service:**

```python
class WISMOInsightsService:
    def __init__(self, analytics_service: WISMOAnalyticsService):
        self.analytics = analytics_service

    async def generate_insights(
        self,
        store_id: UUID,
        date_range: DateRange
    ) -> list[Insight]:
        """Generate actionable insights from WISMO data."""
        insights = []

        # 1. Analyze inquiry patterns
        # 2. Identify fulfillment bottlenecks
        # 3. Compare with industry benchmarks
        # 4. Generate recommendations

        return insights

class Insight(BaseModel):
    type: str  # 'warning', 'opportunity', 'success'
    title: str
    description: str
    recommendation: str
    impact: str  # 'high', 'medium', 'low'
    data_points: dict
```

### 3.7 Customer Satisfaction Tracking

**Location:** `apps/api/app/services/satisfaction.py`

- [ ] Implement post-inquiry satisfaction surveys
- [ ] Track satisfaction scores over time
- [ ] Correlate satisfaction with resolution time
- [ ] Generate satisfaction reports for merchants

**Satisfaction Tracking:**

```python
async def record_satisfaction_feedback(
    inquiry_id: UUID,
    rating: int,  # 1-5 scale
    feedback: str = None
) -> None:
    """Record customer satisfaction after inquiry resolution."""
    # 1. Update inquiry record with satisfaction data
    # 2. Calculate rolling satisfaction averages
    # 3. Trigger alerts for low satisfaction scores

async def get_satisfaction_trends(
    store_id: UUID,
    date_range: DateRange
) -> SatisfactionTrends:
    """Get satisfaction trends over time."""
    # 1. Aggregate satisfaction scores by time period
    # 2. Calculate trends and changes
    # 3. Identify satisfaction drivers
```

### 3.8 Enhanced Chat Service Integration

**Location:** `apps/api/app/services/chat.py` (modify existing)

- [ ] Track inquiry types automatically during conversations
- [ ] Record resolution status and satisfaction
- [ ] Generate analytics events for dashboard
- [ ] Support satisfaction feedback collection

**Analytics Integration:**

```python
async def track_order_inquiry(
    conversation_id: UUID,
    order_number: str,
    inquiry_type: str,
    order_status: str
) -> None:
    """Track order inquiry for analytics."""
    # 1. Create inquiry record
    # 2. Update daily metrics
    # 3. Trigger insight generation if needed

async def mark_inquiry_resolved(
    inquiry_id: UUID,
    resolution_time: timedelta,
    customer_satisfied: bool = None
) -> None:
    """Mark inquiry as resolved with metrics."""
    # 1. Update inquiry record
    # 2. Calculate resolution metrics
    # 3. Update satisfaction scores
```

---

## Files to Create/Modify

| File                                     | Action | Purpose                         |
| ---------------------------------------- | ------ | ------------------------------- |
| `app/services/analytics.py`              | Create | WISMO analytics service         |
| `app/services/insights.py`               | Create | Automated insights generation   |
| `app/services/satisfaction.py`           | Create | Customer satisfaction tracking  |
| `app/models/analytics.py`                | Create | Analytics data models           |
| `app/api/v1/analytics.py`                | Create | Analytics API endpoints         |
| `app/schemas/analytics.py`               | Create | Analytics Pydantic models       |
| `apps/web/src/pages/analytics/wismo.tsx` | Create | WISMO dashboard page            |
| `apps/web/src/components/analytics/`     | Create | Analytics UI components         |
| `apps/web/src/components/orders/`        | Create | Order timeline components       |
| `apps/web/src/hooks/useWISMOMetrics.ts`  | Create | Analytics data fetching hooks   |
| `app/services/chat.py`                   | Modify | Add analytics tracking          |
| `app/workers/analytics_tasks.py`         | Create | Background analytics processing |

---

## Dependencies

```toml
# Add to pyproject.toml (backend)
pandas = "^2.0"              # Data analysis for insights
numpy = "^1.24"              # Numerical computations
```

```json
// Add to package.json (frontend)
{
  "recharts": "^2.8.0", // Charts and data visualization
  "date-fns": "^2.30.0" // Date manipulation for analytics
}
```

---

## Dashboard Routes

| Route                            | Component            | Purpose                   |
| -------------------------------- | -------------------- | ------------------------- |
| `/analytics/wismo`               | WISMODashboard       | Main WISMO analytics page |
| `/analytics/wismo/inquiries`     | InquiryAnalytics     | Detailed inquiry analysis |
| `/analytics/wismo/fulfillment`   | FulfillmentAnalytics | Fulfillment performance   |
| `/orders/{orderNumber}/timeline` | OrderTimeline        | Individual order journey  |

---

## Testing

- [ ] Unit test: Analytics data aggregation functions
- [ ] Unit test: Insight generation algorithms
- [ ] Unit test: Satisfaction score calculations
- [ ] Integration test: Full analytics pipeline
- [ ] Test: Dashboard API endpoints with various date ranges
- [ ] Test: Real-time analytics updates
- [ ] UI test: Dashboard component rendering
- [ ] Performance test: Analytics queries with large datasets

---

## Acceptance Criteria

1. Merchants can view comprehensive WISMO analytics dashboard
2. Inquiry trends are visualized with interactive charts
3. Fulfillment performance metrics are accurate and actionable
4. Order timelines show complete journey from purchase to delivery
5. Automated insights provide valuable recommendations
6. Customer satisfaction tracking works end-to-end
7. Dashboard loads quickly with large datasets
8. Analytics data updates in near real-time

---

## Key Metrics to Track

### Inquiry Metrics

- Total order inquiries per period
- Inquiry rate (inquiries / total orders)
- Inquiry types distribution
- Repeat inquiry rate
- Peak inquiry times/days

### Fulfillment Metrics

- Average time to ship
- Delivery performance by carrier
- Exception rates and causes
- On-time delivery percentage
- Customer satisfaction scores

### Operational Metrics

- Average resolution time
- First-contact resolution rate
- Agent response time
- Customer effort score

---

## Notes

- Consider implementing real-time dashboard updates using WebSockets
- Analytics data should be aggregated daily for performance
- Provide export functionality for analytics data (CSV, PDF reports)
- Consider adding industry benchmarking in future iterations
- Ensure analytics comply with data privacy regulations (GDPR, CCPA)
