# Phase 2: Dashboard & Reporting

> **Parent:** [M7 Analytics & Self-Improvement](../m7-analytics.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 1 (Analytics Pipeline) complete

---

## Goal

Build the executive dashboard and reporting system that visualizes analytics data and provides actionable insights to merchants.

---

## Tasks

### 2.1 Executive Dashboard UI

**Location:** `apps/web/app/(dashboard)/analytics/page.tsx`

- [ ] Create main analytics dashboard page
- [ ] Implement key metrics cards with trend indicators
- [ ] Add conversation resolution breakdown chart
- [ ] Create time-series charts for trends
- [ ] Add responsive design for mobile/tablet

**Dashboard Layout:**

```tsx
'use client';

import { useEffect, useState } from 'react';

import { MetricCard } from '@/components/analytics/metric-card';
import { ResolutionBreakdown } from '@/components/analytics/resolution-breakdown';
import { TrendChart } from '@/components/analytics/trend-chart';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface DashboardMetrics {
  totalConversations: number;
  resolutionRate: number;
  avgResponseTime: number;
  costSavings: number;
  trends: {
    conversations: number;
    resolutionRate: number;
    responseTime: number;
    savings: number;
  };
}

export default function AnalyticsDashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [period, setPeriod] = useState<'day' | 'week' | 'month' | 'quarter'>('month');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardMetrics();
  }, [period]);

  const fetchDashboardMetrics = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/analytics/dashboard?period=${period}`);
      const data = await response.json();
      setMetrics(data);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Conversations"
          value={metrics?.totalConversations || 0}
          trend={metrics?.trends.conversations || 0}
          format="number"
        />
        <MetricCard
          title="Resolution Rate"
          value={metrics?.resolutionRate || 0}
          trend={metrics?.trends.resolutionRate || 0}
          format="percentage"
        />
        <MetricCard
          title="Avg Response Time"
          value={metrics?.avgResponseTime || 0}
          trend={metrics?.trends.responseTime || 0}
          format="duration"
        />
        <MetricCard
          title="Cost Savings"
          value={metrics?.costSavings || 0}
          trend={metrics?.trends.savings || 0}
          format="currency"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Resolution Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <ResolutionBreakdown period={period} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Conversation Trends</CardTitle>
          </CardHeader>
          <CardContent>
            <TrendChart period={period} />
          </CardContent>
        </Card>
      </div>

      {/* ROI Calculator */}
      <Card>
        <CardHeader>
          <CardTitle>ROI Calculator</CardTitle>
        </CardHeader>
        <CardContent>
          <ROICalculator />
        </CardContent>
      </Card>
    </div>
  );
}
```

### 2.2 Reusable Chart Components

**Location:** `apps/web/components/analytics/`

- [ ] Create MetricCard component with trend indicators
- [ ] Build TrendChart component using Chart.js
- [ ] Create ResolutionBreakdown pie/donut chart
- [ ] Add ROICalculator interactive component

**MetricCard Component:**

```tsx
// apps/web/components/analytics/metric-card.tsx
import { Minus, TrendingDown, TrendingUp } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface MetricCardProps {
  title: string;
  value: number;
  trend?: number;
  format: 'number' | 'percentage' | 'currency' | 'duration';
  className?: string;
}

export function MetricCard({ title, value, trend, format, className }: MetricCardProps) {
  const formatValue = (val: number, fmt: string) => {
    switch (fmt) {
      case 'percentage':
        return `${val.toFixed(1)}%`;
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
        }).format(val);
      case 'duration':
        return val < 1000 ? `${val}ms` : `${(val / 1000).toFixed(1)}s`;
      default:
        return new Intl.NumberFormat('en-US').format(val);
    }
  };

  const getTrendIcon = () => {
    if (!trend || trend === 0) return <Minus className="h-4 w-4 text-gray-400" />;
    return trend > 0 ? (
      <TrendingUp className="h-4 w-4 text-green-600" />
    ) : (
      <TrendingDown className="h-4 w-4 text-red-600" />
    );
  };

  const getTrendColor = () => {
    if (!trend || trend === 0) return 'text-gray-400';
    return trend > 0 ? 'text-green-600' : 'text-red-600';
  };

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {getTrendIcon()}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{formatValue(value, format)}</div>
        {trend !== undefined && (
          <p className={`text-xs ${getTrendColor()}`}>
            {trend > 0 ? '+' : ''}
            {trend.toFixed(1)}% from last period
          </p>
        )}
      </CardContent>
    </Card>
  );
}
```

**TrendChart Component:**

```tsx
// apps/web/components/analytics/trend-chart.tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import {
  CategoryScale,
  Chart as ChartJS,
  ChartOptions,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface TrendChartProps {
  period: 'day' | 'week' | 'month' | 'quarter';
}

export function TrendChart({ period }: TrendChartProps) {
  const [chartData, setChartData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTrendData();
  }, [period]);

  const fetchTrendData = async () => {
    setLoading(true);
    try {
      const endDate = new Date();
      const startDate = new Date();

      // Calculate start date based on period
      switch (period) {
        case 'day':
          startDate.setDate(endDate.getDate() - 7);
          break;
        case 'week':
          startDate.setDate(endDate.getDate() - 28);
          break;
        case 'month':
          startDate.setMonth(endDate.getMonth() - 6);
          break;
        case 'quarter':
          startDate.setMonth(endDate.getMonth() - 12);
          break;
      }

      const response = await fetch(
        `/api/analytics/conversations/trends?start_date=${startDate.toISOString().split('T')[0]}&end_date=${endDate.toISOString().split('T')[0]}&granularity=${period === 'day' ? 'day' : period === 'week' ? 'week' : 'month'}`
      );
      const data = await response.json();

      setChartData({
        labels: data.map((d: any) => d.date),
        datasets: [
          {
            label: 'Conversations',
            data: data.map((d: any) => d.total_conversations),
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.1,
          },
          {
            label: 'Resolution Rate (%)',
            data: data.map((d: any) => d.resolution_rate * 100),
            borderColor: 'rgb(34, 197, 94)',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            tension: 0.1,
            yAxisID: 'y1',
          },
        ],
      });
    } catch (error) {
      console.error('Failed to fetch trend data:', error);
    } finally {
      setLoading(false);
    }
  };

  const options: ChartOptions<'line'> = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
    },
    scales: {
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        grid: {
          drawOnChartArea: false,
        },
      },
    },
  };

  if (loading) {
    return <div className="h-64 animate-pulse rounded bg-gray-200"></div>;
  }

  return chartData ? <Line data={chartData} options={options} /> : null;
}
```

### 2.3 ROI Calculator Component

**Location:** `apps/web/components/analytics/roi-calculator.tsx`

- [ ] Interactive ROI calculator with configurable parameters
- [ ] Real-time calculation updates
- [ ] Visual representation of savings
- [ ] Export ROI report functionality

```tsx
'use client';

import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface ROIData {
  totalConversations: number;
  aiResolvedConversations: number;
  savings: number;
  roiPercentage: number;
  humanCost: number;
  aiCost: number;
}

export function ROICalculator() {
  const [periodDays, setPeriodDays] = useState(30);
  const [humanCostPerHour, setHumanCostPerHour] = useState(25);
  const [avgConversationTime, setAvgConversationTime] = useState(8);
  const [aiCostPerConversation, setAiCostPerConversation] = useState(0.05);
  const [roiData, setRoiData] = useState<ROIData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    calculateROI();
  }, [periodDays, humanCostPerHour, avgConversationTime, aiCostPerConversation]);

  const calculateROI = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        period_days: periodDays.toString(),
        human_cost_per_hour: humanCostPerHour.toString(),
        avg_conversation_time_minutes: avgConversationTime.toString(),
        ai_cost_per_conversation: aiCostPerConversation.toString(),
      });

      const response = await fetch(`/api/analytics/roi?${params}`);
      const data = await response.json();
      setRoiData(data);
    } catch (error) {
      console.error('Failed to calculate ROI:', error);
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async () => {
    // Generate and download ROI report
    const reportData = {
      period: `${periodDays} days`,
      parameters: {
        humanCostPerHour,
        avgConversationTime,
        aiCostPerConversation,
      },
      results: roiData,
      generatedAt: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `roi-report-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div>
          <Label htmlFor="period">Period (days)</Label>
          <Input
            id="period"
            type="number"
            value={periodDays}
            onChange={(e) => setPeriodDays(Number(e.target.value))}
            min={1}
            max={365}
          />
        </div>
        <div>
          <Label htmlFor="human-cost">Human Agent Cost ($/hour)</Label>
          <Input
            id="human-cost"
            type="number"
            value={humanCostPerHour}
            onChange={(e) => setHumanCostPerHour(Number(e.target.value))}
            min={0}
            step={0.01}
          />
        </div>
        <div>
          <Label htmlFor="conversation-time">Avg Conversation Time (min)</Label>
          <Input
            id="conversation-time"
            type="number"
            value={avgConversationTime}
            onChange={(e) => setAvgConversationTime(Number(e.target.value))}
            min={0}
            step={0.1}
          />
        </div>
        <div>
          <Label htmlFor="ai-cost">AI Cost per Conversation ($)</Label>
          <Input
            id="ai-cost"
            type="number"
            value={aiCostPerConversation}
            onChange={(e) => setAiCostPerConversation(Number(e.target.value))}
            min={0}
            step={0.001}
          />
        </div>
      </div>

      {/* Results */}
      {roiData && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Total Savings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">
                ${roiData.savings.toLocaleString()}
              </div>
              <p className="text-sm text-gray-600">Over {periodDays} days</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">ROI</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-600">
                {roiData.roiPercentage.toFixed(0)}%
              </div>
              <p className="text-sm text-gray-600">Return on investment</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">AI Resolution Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-purple-600">
                {((roiData.aiResolvedConversations / roiData.totalConversations) * 100).toFixed(1)}%
              </div>
              <p className="text-sm text-gray-600">
                {roiData.aiResolvedConversations} of {roiData.totalConversations} conversations
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Export */}
      <div className="flex justify-end">
        <Button onClick={exportReport} disabled={!roiData}>
          <Download className="mr-2 h-4 w-4" />
          Export Report
        </Button>
      </div>
    </div>
  );
}
```

### 2.4 Email Reporting System

**Location:** `apps/api/app/services/reports.py`

- [ ] Weekly email report generation
- [ ] Customizable report templates
- [ ] Email delivery via service (SendGrid/SES)
- [ ] Report scheduling and management

```python
from jinja2 import Template
from datetime import datetime, timedelta
from typing import Dict, Any, List
import asyncio

class ReportService:
    def __init__(self, db: AsyncSession, email_service: EmailService):
        self.db = db
        self.email_service = email_service

    async def generate_weekly_report(self, store_id: UUID) -> Dict[str, Any]:
        """Generate weekly analytics report data."""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)

        # Get current week metrics
        current_metrics = await calculate_period_metrics(store_id, start_date, end_date)

        # Get previous week for comparison
        prev_start = start_date - timedelta(days=7)
        prev_end = start_date - timedelta(days=1)
        previous_metrics = await calculate_period_metrics(store_id, prev_start, prev_end)

        # Get top conversation topics
        top_topics = await self._get_top_conversation_topics(store_id, start_date, end_date)

        # Calculate ROI
        roi_calc = await AnalyticsService(self.db).calculate_roi(store_id, 7)

        return {
            "period": f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}",
            "current_metrics": current_metrics,
            "previous_metrics": previous_metrics,
            "top_topics": top_topics,
            "roi": roi_calc,
            "generated_at": datetime.utcnow().isoformat()
        }

    async def send_weekly_report(self, store_id: UUID) -> bool:
        """Generate and send weekly report email."""
        try:
            # Get store and user info
            store = await self.db.get(Store, store_id)
            if not store:
                return False

            # Generate report data
            report_data = await self.generate_weekly_report(store_id)

            # Render email template
            html_content = await self._render_email_template(
                "weekly_report.html",
                {**report_data, "store": store}
            )

            # Send email
            await self.email_service.send_email(
                to=store.owner_email,
                subject=f"Weekly Analytics Report - {store.name}",
                html_content=html_content
            )

            return True
        except Exception as e:
            logger.error(f"Failed to send weekly report for store {store_id}: {e}")
            return False

    async def _render_email_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email template with context data."""
        template_path = f"app/templates/emails/{template_name}"
        with open(template_path, 'r') as f:
            template = Template(f.read())
        return template.render(**context)

    async def _get_top_conversation_topics(
        self,
        store_id: UUID,
        start_date: date,
        end_date: date,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get most common conversation topics for the period."""
        # This would analyze conversation content to extract topics
        # For now, return placeholder data
        return [
            {"topic": "Shipping", "count": 45, "percentage": 23.5},
            {"topic": "Returns", "count": 32, "percentage": 16.7},
            {"topic": "Product Info", "count": 28, "percentage": 14.6},
            {"topic": "Sizing", "count": 24, "percentage": 12.5},
            {"topic": "Payment", "count": 18, "percentage": 9.4},
        ]

# Email template (apps/api/app/templates/emails/weekly_report.html)
WEEKLY_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Weekly Analytics Report</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .header { background: #f8f9fa; padding: 20px; text-align: center; }
        .metrics { display: flex; justify-content: space-around; margin: 20px 0; }
        .metric { text-align: center; padding: 15px; }
        .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
        .trend-up { color: #28a745; }
        .trend-down { color: #dc3545; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Weekly Analytics Report</h1>
        <p>{{ store.name }} - {{ period }}</p>
    </div>

    <div class="metrics">
        <div class="metric">
            <div class="metric-value">{{ current_metrics.metrics.total_conversations }}</div>
            <div>Conversations</div>
            {% if current_metrics.growth_rate %}
                <div class="{% if current_metrics.growth_rate > 0 %}trend-up{% else %}trend-down{% endif %}">
                    {{ "+" if current_metrics.growth_rate > 0 }}{{ (current_metrics.growth_rate * 100)|round(1) }}%
                </div>
            {% endif %}
        </div>

        <div class="metric">
            <div class="metric-value">{{ (current_metrics.metrics.resolution_rate * 100)|round(1) }}%</div>
            <div>Resolution Rate</div>
        </div>

        <div class="metric">
            <div class="metric-value">${{ roi.savings|round(0) }}</div>
            <div>Cost Savings</div>
        </div>
    </div>

    <h3>Top Conversation Topics</h3>
    <ul>
        {% for topic in top_topics %}
            <li>{{ topic.topic }}: {{ topic.count }} conversations ({{ topic.percentage }}%)</li>
        {% endfor %}
    </ul>

    <p>View your full analytics dashboard: <a href="https://app.reva.ai/analytics">Open Dashboard</a></p>
</body>
</html>
"""
```

### 2.5 Report Scheduling

**Location:** `apps/api/app/workers/report_tasks.py`

- [ ] Celery task for weekly report generation
- [ ] Configurable report schedules per store
- [ ] Error handling and retry logic
- [ ] Report delivery tracking

```python
from celery import Celery
from celery.schedules import crontab

@celery.task
async def send_weekly_reports():
    """Send weekly reports to all stores that have them enabled."""
    async with get_db_session() as db:
        # Get stores with weekly reports enabled
        stores = await db.execute(
            select(Store).where(Store.weekly_reports_enabled == True)
        )

        report_service = ReportService(db, EmailService())

        for store in stores.scalars():
            try:
                success = await report_service.send_weekly_report(store.id)
                if success:
                    logger.info(f"Weekly report sent successfully for store {store.id}")
                else:
                    logger.error(f"Failed to send weekly report for store {store.id}")
            except Exception as e:
                logger.error(f"Error sending weekly report for store {store.id}: {e}")

# Schedule weekly reports for Monday mornings
celery.conf.beat_schedule = {
    'send-weekly-reports': {
        'task': 'app.workers.report_tasks.send_weekly_reports',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),  # Monday 9 AM
    },
}
```

---

## Files to Create/Modify

| File                                                     | Action | Purpose                           |
| -------------------------------------------------------- | ------ | --------------------------------- |
| `apps/web/app/(dashboard)/analytics/page.tsx`            | Create | Main analytics dashboard page     |
| `apps/web/components/analytics/metric-card.tsx`          | Create | Reusable metric display component |
| `apps/web/components/analytics/trend-chart.tsx`          | Create | Time-series chart component       |
| `apps/web/components/analytics/resolution-breakdown.tsx` | Create | Resolution pie chart component    |
| `apps/web/components/analytics/roi-calculator.tsx`       | Create | Interactive ROI calculator        |
| `apps/api/app/services/reports.py`                       | Create | Report generation service         |
| `apps/api/app/workers/report_tasks.py`                   | Create | Email report scheduling           |
| `apps/api/app/templates/emails/weekly_report.html`       | Create | Email report template             |
| `apps/web/lib/analytics-api.ts`                          | Create | Frontend API client               |

---

## Dependencies

```json
// Add to apps/web/package.json
{
  "chart.js": "^4.4.0",
  "react-chartjs-2": "^5.2.0"
}
```

```toml
# Add to apps/api/pyproject.toml
jinja2 = "^3.1"              # Email templating
sendgrid = "^6.10"           # Email delivery (or AWS SES)
```

---

## Testing

- [ ] Unit test: dashboard components render correctly
- [ ] Unit test: chart components handle data properly
- [ ] Unit test: ROI calculator produces correct results
- [ ] Integration test: email report generation and delivery
- [ ] E2E test: full dashboard user journey
- [ ] Performance test: dashboard loads within 2 seconds

---

## Acceptance Criteria

1. Dashboard displays key metrics with proper formatting
2. Charts update dynamically based on period selection
3. ROI calculator provides accurate, real-time calculations
4. Weekly email reports are generated and delivered successfully
5. Dashboard is responsive and works on mobile devices
6. All data is properly scoped by store (multi-tenant)

---

## Notes

- Use Chart.js for consistent, performant charts
- Implement proper loading states and error handling
- Consider adding export functionality for all charts
- Add keyboard navigation for accessibility
- Implement proper caching for dashboard API calls
