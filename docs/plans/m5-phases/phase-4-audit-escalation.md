# Phase 4: Audit Logging & Escalation

> **Parent:** [M5 Full Action Agent](../m5-action-agent.md)  
> **Duration:** 0.5 weeks  
> **Status:** Not Started  
> **Dependencies:** Phase 1-3 complete

---

## Goal

Complete the action agent system with comprehensive audit logging and escalation flows. Ensure all actions are tracked for compliance and provide seamless handoff to human agents when needed.

---

## Tasks

### 4.1 Audit Service Implementation

**Location:** `apps/api/app/services/audit.py`

- [ ] Implement comprehensive audit logging
- [ ] Track all action attempts, confirmations, and results
- [ ] Support audit queries and reporting
- [ ] Ensure GDPR compliance for audit data

```python
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.dialects.postgresql import insert

from app.models.permissions import ActionAudit
from app.schemas.permissions import ActionType

class AuditService:
    """Service for comprehensive audit logging of all actions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_action_attempt(
        self,
        store_id: UUID,
        conversation_id: UUID,
        action_type: ActionType,
        action_data: Dict[str, Any],
        customer_info: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """Log an action attempt."""
        audit_record = ActionAudit(
            id=uuid4(),
            store_id=store_id,
            conversation_id=conversation_id,
            action_type=action_type.value,
            action_data={
                **action_data,
                "customer_info": customer_info or {},
                "timestamp": datetime.utcnow().isoformat()
            },
            status="pending"
        )

        self.db.add(audit_record)
        await self.db.flush()
        return audit_record.id

    async def log_action_confirmation(
        self,
        audit_id: UUID,
        confirmed: bool,
        confirmation_method: str = "widget"
    ) -> None:
        """Log customer confirmation or cancellation."""
        result = await self.db.execute(
            select(ActionAudit).where(ActionAudit.id == audit_id)
        )
        audit_record = result.scalar_one_or_none()

        if audit_record:
            audit_record.customer_confirmed_at = datetime.utcnow()
            audit_record.status = "confirmed" if confirmed else "cancelled"

            # Update action_data with confirmation details
            audit_record.action_data = {
                **audit_record.action_data,
                "confirmation": {
                    "confirmed": confirmed,
                    "method": confirmation_method,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }

            await self.db.commit()

    async def log_action_success(
        self,
        audit_id: UUID,
        result_data: Dict[str, Any]
    ) -> None:
        """Log successful action execution."""
        result = await self.db.execute(
            select(ActionAudit).where(ActionAudit.id == audit_id)
        )
        audit_record = result.scalar_one_or_none()

        if audit_record:
            audit_record.executed_at = datetime.utcnow()
            audit_record.status = "executed"

            # Store execution results
            audit_record.action_data = {
                **audit_record.action_data,
                "execution_result": result_data,
                "executed_timestamp": datetime.utcnow().isoformat()
            }

            await self.db.commit()

    async def log_action_failure(
        self,
        audit_id: UUID,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log failed action execution."""
        result = await self.db.execute(
            select(ActionAudit).where(ActionAudit.id == audit_id)
        )
        audit_record = result.scalar_one_or_none()

        if audit_record:
            audit_record.status = "failed"
            audit_record.error_message = error_message

            # Store error details
            audit_record.action_data = {
                **audit_record.action_data,
                "error": {
                    "message": error_message,
                    "details": error_details or {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }

            await self.db.commit()

    async def get_store_audit_log(
        self,
        store_id: UUID,
        limit: int = 100,
        offset: int = 0,
        action_type: Optional[ActionType] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ActionAudit]:
        """Get audit log for a store with filtering."""
        query = select(ActionAudit).where(ActionAudit.store_id == store_id)

        if action_type:
            query = query.where(ActionAudit.action_type == action_type.value)

        if status:
            query = query.where(ActionAudit.status == status)

        if start_date:
            query = query.where(ActionAudit.created_at >= start_date)

        if end_date:
            query = query.where(ActionAudit.created_at <= end_date)

        query = query.order_by(desc(ActionAudit.created_at)).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_action_statistics(
        self,
        store_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get action statistics for the store."""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get all actions in the time period
        result = await self.db.execute(
            select(ActionAudit).where(
                and_(
                    ActionAudit.store_id == store_id,
                    ActionAudit.created_at >= start_date
                )
            )
        )
        actions = result.scalars().all()

        # Calculate statistics
        total_actions = len(actions)
        successful_actions = len([a for a in actions if a.status == "executed"])
        failed_actions = len([a for a in actions if a.status == "failed"])
        cancelled_actions = len([a for a in actions if a.status == "cancelled"])

        # Group by action type
        action_type_counts = {}
        for action in actions:
            action_type = action.action_type
            if action_type not in action_type_counts:
                action_type_counts[action_type] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "cancelled": 0
                }

            action_type_counts[action_type]["total"] += 1
            if action.status == "executed":
                action_type_counts[action_type]["successful"] += 1
            elif action.status == "failed":
                action_type_counts[action_type]["failed"] += 1
            elif action.status == "cancelled":
                action_type_counts[action_type]["cancelled"] += 1

        return {
            "period_days": days,
            "total_actions": total_actions,
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "cancelled_actions": cancelled_actions,
            "success_rate": successful_actions / total_actions if total_actions > 0 else 0,
            "action_types": action_type_counts
        }
```

### 4.2 Escalation Service

**Location:** `apps/api/app/services/escalation.py`

- [ ] Implement escalation triggers and rules
- [ ] Support manual and automatic escalation
- [ ] Integration with external ticketing systems
- [ ] Notification system for human agents

```python
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.conversation import Conversation
from app.models.store import Store
from app.services.notification import NotificationService

class EscalationReason(str, Enum):
    CUSTOMER_REQUEST = "customer_request"
    ACTION_FAILED = "action_failed"
    PERMISSION_DENIED = "permission_denied"
    COMPLEX_ISSUE = "complex_issue"
    TIMEOUT = "timeout"
    ERROR_THRESHOLD = "error_threshold"

class EscalationService:
    """Service for escalating conversations to human agents."""

    def __init__(self, db: AsyncSession, notification_service: NotificationService):
        self.db = db
        self.notification_service = notification_service

    async def escalate_conversation(
        self,
        conversation_id: UUID,
        reason: EscalationReason,
        context: Optional[Dict[str, Any]] = None,
        customer_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Escalate a conversation to human agents."""

        # Get conversation details
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Get store details
        result = await self.db.execute(
            select(Store).where(Store.id == conversation.store_id)
        )
        store = result.scalar_one_or_none()

        # Create escalation record
        escalation_data = {
            "conversation_id": conversation_id,
            "store_id": conversation.store_id,
            "reason": reason.value,
            "context": context or {},
            "customer_message": customer_message,
            "escalated_at": datetime.utcnow(),
            "status": "pending"
        }

        # Update conversation status
        conversation.status = "escalated"
        conversation.escalated_at = datetime.utcnow()
        conversation.escalation_reason = reason.value

        # Send notifications
        await self._notify_human_agents(store, escalation_data)

        # Send customer notification
        await self._notify_customer_escalation(conversation, reason)

        await self.db.commit()

        return escalation_data

    async def check_escalation_triggers(
        self,
        conversation_id: UUID,
        action_type: Optional[str] = None,
        error_count: int = 0
    ) -> Optional[EscalationReason]:
        """Check if conversation should be escalated based on triggers."""

        # Get conversation
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            return None

        # Check error threshold
        if error_count >= 3:
            return EscalationReason.ERROR_THRESHOLD

        # Check conversation duration (if too long)
        conversation_duration = datetime.utcnow() - conversation.created_at
        if conversation_duration.total_seconds() > 1800:  # 30 minutes
            return EscalationReason.TIMEOUT

        # Check message count (if too many back-and-forth)
        if len(conversation.messages) > 20:
            return EscalationReason.COMPLEX_ISSUE

        return None

    async def _notify_human_agents(
        self,
        store: Store,
        escalation_data: Dict[str, Any]
    ) -> None:
        """Notify human agents about escalation."""

        # Send email notification
        await self.notification_service.send_email(
            to=store.support_email,
            subject=f"Customer Conversation Escalated - {store.name}",
            template="escalation_notification",
            data={
                "store_name": store.name,
                "conversation_id": escalation_data["conversation_id"],
                "reason": escalation_data["reason"],
                "escalated_at": escalation_data["escalated_at"],
                "dashboard_url": f"https://app.reva.ai/dashboard/conversations/{escalation_data['conversation_id']}"
            }
        )

        # Send webhook if configured
        if store.escalation_webhook_url:
            await self.notification_service.send_webhook(
                url=store.escalation_webhook_url,
                data=escalation_data
            )

    async def _notify_customer_escalation(
        self,
        conversation: Conversation,
        reason: EscalationReason
    ) -> None:
        """Notify customer about escalation."""

        escalation_messages = {
            EscalationReason.CUSTOMER_REQUEST: "I've connected you with a human agent who will help you shortly.",
            EscalationReason.ACTION_FAILED: "I encountered an issue processing your request. A human agent will help you resolve this.",
            EscalationReason.PERMISSION_DENIED: "This request requires human approval. An agent will review and assist you.",
            EscalationReason.COMPLEX_ISSUE: "This seems like a complex issue. Let me connect you with a human agent for better assistance.",
            EscalationReason.TIMEOUT: "I want to make sure you get the best help. Let me connect you with a human agent.",
            EscalationReason.ERROR_THRESHOLD: "I'm having trouble with your request. A human agent will take over to help you."
        }

        message = escalation_messages.get(reason, "I'm connecting you with a human agent for assistance.")

        # Add escalation message to conversation
        # This would integrate with your message storage system
        pass

    async def resolve_escalation(
        self,
        conversation_id: UUID,
        resolution_notes: str,
        resolved_by: str
    ) -> None:
        """Mark escalation as resolved."""

        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if conversation:
            conversation.status = "resolved"
            conversation.resolved_at = datetime.utcnow()
            conversation.resolved_by = resolved_by
            conversation.resolution_notes = resolution_notes

            await self.db.commit()
```

### 4.3 Audit Dashboard

**Location:** `apps/web/app/dashboard/audit/page.tsx`

- [ ] Create audit log dashboard
- [ ] Support filtering and search
- [ ] Export audit reports
- [ ] Real-time action monitoring

```typescript
'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface AuditRecord {
  id: string;
  action_type: string;
  status: string;
  created_at: string;
  executed_at?: string;
  action_data: any;
  error_message?: string;
}

interface AuditStats {
  total_actions: number;
  successful_actions: number;
  failed_actions: number;
  cancelled_actions: number;
  success_rate: number;
  action_types: Record<string, any>;
}

export default function AuditDashboard() {
  const [auditRecords, setAuditRecords] = useState<AuditRecord[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    action_type: '',
    status: '',
    date_range: '30'
  });

  useEffect(() => {
    fetchAuditData();
    fetchStats();
  }, [filters]);

  const fetchAuditData = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.action_type) params.append('action_type', filters.action_type);
      if (filters.status) params.append('status', filters.status);

      const response = await fetch(`/api/v1/audit?${params}`);
      const data = await response.json();
      setAuditRecords(data);
    } catch (error) {
      console.error('Failed to fetch audit data:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`/api/v1/audit/stats?days=${filters.date_range}`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      executed: 'default',
      failed: 'destructive',
      cancelled: 'secondary',
      pending: 'outline'
    };

    return (
      <Badge variant={variants[status] || 'outline'}>
        {status}
      </Badge>
    );
  };

  const getActionIcon = (actionType: string) => {
    const icons = {
      cancel_order: '❌',
      process_refund: '💰',
      initiate_return: '📦',
      apply_discount: '🏷️',
      update_address: '📍',
      lookup_order: '🔍',
      send_tracking: '📬'
    };

    return icons[actionType] || '⚡';
  };

  const exportAuditLog = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.action_type) params.append('action_type', filters.action_type);
      if (filters.status) params.append('status', filters.status);
      params.append('format', 'csv');

      const response = await fetch(`/api/v1/audit/export?${params}`);
      const blob = await response.blob();

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-log-${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export audit log:', error);
    }
  };

  if (loading) {
    return <div>Loading audit data...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Audit Log</h1>
          <p className="text-muted-foreground">
            Track all AI agent actions and their outcomes
          </p>
        </div>
        <Button onClick={exportAuditLog}>
          Export CSV
        </Button>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_actions}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {(stats.success_rate * 100).toFixed(1)}%
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Failed Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{stats.failed_actions}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Cancelled Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">{stats.cancelled_actions}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Select
              value={filters.action_type}
              onValueChange={(value) => setFilters({...filters, action_type: value})}
            >
              <SelectTrigger>
                <SelectValue placeholder="All Action Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Action Types</SelectItem>
                <SelectItem value="cancel_order">Cancel Order</SelectItem>
                <SelectItem value="process_refund">Process Refund</SelectItem>
                <SelectItem value="initiate_return">Initiate Return</SelectItem>
                <SelectItem value="apply_discount">Apply Discount</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={filters.status}
              onValueChange={(value) => setFilters({...filters, status: value})}
            >
              <SelectTrigger>
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Statuses</SelectItem>
                <SelectItem value="executed">Executed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={filters.date_range}
              onValueChange={(value) => setFilters({...filters, date_range: value})}
            >
              <SelectTrigger>
                <SelectValue placeholder="Date Range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Audit Records Table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Action</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Details</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Duration</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {auditRecords.map((record) => (
                <TableRow key={record.id}>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <span>{getActionIcon(record.action_type)}</span>
                      <span className="font-medium">
                        {record.action_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(record.status)}
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">
                      {record.action_data.order_id && (
                        <div>Order: #{record.action_data.order_id}</div>
                      )}
                      {record.action_data.amount && (
                        <div>Amount: ${record.action_data.amount}</div>
                      )}
                      {record.error_message && (
                        <div className="text-red-600">Error: {record.error_message}</div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {new Date(record.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    {record.executed_at ? (
                      `${Math.round((new Date(record.executed_at).getTime() - new Date(record.created_at).getTime()) / 1000)}s`
                    ) : (
                      '-'
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
```

### 4.4 Audit API Endpoints

**Location:** `apps/api/app/api/v1/audit.py`

- [ ] `GET /api/v1/audit` - List audit records with filtering
- [ ] `GET /api/v1/audit/stats` - Get audit statistics
- [ ] `GET /api/v1/audit/export` - Export audit data
- [ ] `GET /api/v1/audit/{audit_id}` - Get specific audit record

```python
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List
from datetime import datetime, timedelta
import csv
import io

from app.core.deps import get_db, get_current_store
from app.models.store import Store
from app.services.audit import AuditService
from app.schemas.permissions import ActionType

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/")
async def list_audit_records(
    action_type: Optional[ActionType] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    store: Store = Depends(get_current_store),
    db: AsyncSession = Depends(get_db)
):
    """List audit records for the current store."""
    audit_service = AuditService(db)

    records = await audit_service.get_store_audit_log(
        store_id=store.id,
        limit=limit,
        offset=offset,
        action_type=action_type,
        status=status
    )

    return [
        {
            "id": str(record.id),
            "action_type": record.action_type,
            "status": record.status,
            "action_data": record.action_data,
            "created_at": record.created_at.isoformat(),
            "executed_at": record.executed_at.isoformat() if record.executed_at else None,
            "error_message": record.error_message
        }
        for record in records
    ]

@router.get("/stats")
async def get_audit_statistics(
    days: int = Query(30, ge=1, le=365),
    store: Store = Depends(get_current_store),
    db: AsyncSession = Depends(get_db)
):
    """Get audit statistics for the current store."""
    audit_service = AuditService(db)

    stats = await audit_service.get_action_statistics(
        store_id=store.id,
        days=days
    )

    return stats

@router.get("/export")
async def export_audit_data(
    format: str = Query("csv", regex="^(csv|json)$"),
    action_type: Optional[ActionType] = None,
    status: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    store: Store = Depends(get_current_store),
    db: AsyncSession = Depends(get_db)
):
    """Export audit data in CSV or JSON format."""
    audit_service = AuditService(db)

    start_date = datetime.utcnow() - timedelta(days=days)
    records = await audit_service.get_store_audit_log(
        store_id=store.id,
        limit=10000,  # Large limit for export
        action_type=action_type,
        status=status,
        start_date=start_date
    )

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "ID", "Action Type", "Status", "Created At", "Executed At",
            "Order ID", "Amount", "Error Message"
        ])

        # Write data
        for record in records:
            writer.writerow([
                str(record.id),
                record.action_type,
                record.status,
                record.created_at.isoformat(),
                record.executed_at.isoformat() if record.executed_at else "",
                record.action_data.get("order_id", ""),
                record.action_data.get("amount", ""),
                record.error_message or ""
            ])

        csv_content = output.getvalue()
        output.close()

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit-{store.id}-{datetime.now().strftime('%Y%m%d')}.csv"}
        )

    else:  # JSON format
        data = [
            {
                "id": str(record.id),
                "action_type": record.action_type,
                "status": record.status,
                "action_data": record.action_data,
                "created_at": record.created_at.isoformat(),
                "executed_at": record.executed_at.isoformat() if record.executed_at else None,
                "error_message": record.error_message
            }
            for record in records
        ]

        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=audit-{store.id}-{datetime.now().strftime('%Y%m%d')}.json"}
        )

@router.get("/{audit_id}")
async def get_audit_record(
    audit_id: UUID,
    store: Store = Depends(get_current_store),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific audit record."""
    result = await db.execute(
        select(ActionAudit).where(
            and_(
                ActionAudit.id == audit_id,
                ActionAudit.store_id == store.id
            )
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Audit record not found")

    return {
        "id": str(record.id),
        "action_type": record.action_type,
        "status": record.status,
        "action_data": record.action_data,
        "created_at": record.created_at.isoformat(),
        "executed_at": record.executed_at.isoformat() if record.executed_at else None,
        "customer_confirmed_at": record.customer_confirmed_at.isoformat() if record.customer_confirmed_at else None,
        "error_message": record.error_message
    }
```

---

## Files to Create/Modify

| File                                    | Action | Purpose                       |
| --------------------------------------- | ------ | ----------------------------- |
| `app/services/audit.py`                 | Create | Comprehensive audit logging   |
| `app/services/escalation.py`            | Create | Escalation management         |
| `app/services/notification.py`          | Create | Notification service          |
| `app/api/v1/audit.py`                   | Create | Audit API endpoints           |
| `apps/web/app/dashboard/audit/page.tsx` | Create | Audit dashboard UI            |
| `app/models/conversation.py`            | Modify | Add escalation fields         |
| `app/models/store.py`                   | Modify | Add escalation webhook config |

---

## Dependencies

```toml
# No new Python dependencies required
```

---

## Testing

- [ ] Unit test: audit logging for all action states
- [ ] Unit test: escalation trigger conditions
- [ ] Unit test: audit statistics calculations
- [ ] Integration test: full audit trail from action to completion
- [ ] E2E test: audit dashboard functionality
- [ ] Test: audit data export in multiple formats

---

## Acceptance Criteria

1. All actions are logged with complete audit trail
2. Audit logs include timestamps, user info, and action details
3. Dashboard provides clear visibility into action history
4. Export functionality works for compliance reporting
5. Escalation triggers work automatically and manually
6. Human agents receive proper notifications
7. Audit data is GDPR compliant and secure

---

## Notes

- Ensure audit logs are immutable once created
- Consider data retention policies for audit logs
- Plan for audit log archiving for long-term storage
- Implement proper access controls for audit data
