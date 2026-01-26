# Phase 1: Permission System & Settings

> **Parent:** [M5 Full Action Agent](../m5-action-agent.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** M1-M4 complete, Shopify OAuth integration

---

## Goal

Build the foundational permission system that controls which actions the agent can perform, with what limits, and under what conditions. This is the safety layer that prevents unauthorized actions.

---

## Tasks

### 1.1 Permission Database Schema

**Location:** `apps/api/alembic/versions/`

- [ ] Create `action_permissions` table
- [ ] Create `action_limits` table
- [ ] Create `action_audit` table
- [ ] Add permission fields to `stores` table

**Database Schema:**

```sql
-- Action permissions per store
CREATE TABLE action_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL, -- 'cancel_order', 'process_refund', etc.
    enabled BOOLEAN DEFAULT FALSE,
    requires_confirmation BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(store_id, action_type)
);

-- Limits for specific actions
CREATE TABLE action_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL,
    limit_type VARCHAR(30) NOT NULL, -- 'max_amount', 'max_percentage', 'time_window'
    limit_value DECIMAL(10,2),
    time_window_hours INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit trail for all actions
CREATE TABLE action_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id),
    action_type VARCHAR(50) NOT NULL,
    action_data JSONB NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'pending', 'confirmed', 'executed', 'failed', 'cancelled'
    customer_confirmed_at TIMESTAMP WITH TIME ZONE,
    executed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 1.2 Permission Models

**Location:** `apps/api/app/models/permissions.py`

- [ ] Create `ActionPermission` SQLAlchemy model
- [ ] Create `ActionLimit` SQLAlchemy model
- [ ] Create `ActionAudit` SQLAlchemy model
- [ ] Add relationships to `Store` model

```python
from sqlalchemy import Column, String, Boolean, Decimal, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

class ActionPermission(Base, TimestampMixin):
    __tablename__ = "action_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(50), nullable=False)
    enabled = Column(Boolean, default=False)
    requires_confirmation = Column(Boolean, default=True)

    store = relationship("Store", back_populates="action_permissions")

    __table_args__ = (UniqueConstraint("store_id", "action_type"),)

class ActionLimit(Base, TimestampMixin):
    __tablename__ = "action_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(50), nullable=False)
    limit_type = Column(String(30), nullable=False)  # 'max_amount', 'max_percentage', 'time_window'
    limit_value = Column(Decimal(10, 2))
    time_window_hours = Column(Integer)

    store = relationship("Store", back_populates="action_limits")

class ActionAudit(Base, TimestampMixin):
    __tablename__ = "action_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"))
    action_type = Column(String(50), nullable=False)
    action_data = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False)  # 'pending', 'confirmed', 'executed', 'failed', 'cancelled'
    customer_confirmed_at = Column(DateTime(timezone=True))
    executed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)

    store = relationship("Store", back_populates="action_audits")
    conversation = relationship("Conversation")
```

### 1.3 Permission Schemas

**Location:** `apps/api/app/schemas/permissions.py`

- [ ] Create Pydantic schemas for permission management
- [ ] Include validation for action types and limits
- [ ] Support bulk permission updates

```python
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class ActionType(str, Enum):
    LOOKUP_ORDER = "lookup_order"
    SEND_TRACKING = "send_tracking"
    UPDATE_ADDRESS = "update_address"
    CANCEL_ORDER = "cancel_order"
    INITIATE_RETURN = "initiate_return"
    PROCESS_REFUND = "process_refund"
    APPLY_DISCOUNT = "apply_discount"

class LimitType(str, Enum):
    MAX_AMOUNT = "max_amount"
    MAX_PERCENTAGE = "max_percentage"
    TIME_WINDOW = "time_window"

class ActionPermissionBase(BaseModel):
    action_type: ActionType
    enabled: bool = False
    requires_confirmation: bool = True

class ActionPermissionCreate(ActionPermissionBase):
    pass

class ActionPermissionUpdate(BaseModel):
    enabled: Optional[bool] = None
    requires_confirmation: Optional[bool] = None

class ActionPermissionResponse(ActionPermissionBase):
    id: UUID
    store_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ActionLimitBase(BaseModel):
    action_type: ActionType
    limit_type: LimitType
    limit_value: Optional[Decimal] = None
    time_window_hours: Optional[int] = None

class ActionLimitCreate(ActionLimitBase):
    pass

class ActionLimitResponse(ActionLimitBase):
    id: UUID
    store_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### 1.4 Permission Service

**Location:** `apps/api/app/services/permissions.py`

- [ ] Implement permission checking logic
- [ ] Support limit validation (amount, percentage, time windows)
- [ ] Cache permissions for performance
- [ ] Handle default permissions for new stores

```python
from typing import Dict, List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.permissions import ActionPermission, ActionLimit, ActionAudit
from app.schemas.permissions import ActionType, LimitType

class PermissionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_action_permission(
        self,
        store_id: UUID,
        action_type: ActionType,
        action_data: Optional[Dict] = None
    ) -> tuple[bool, bool, Optional[str]]:
        """
        Check if action is permitted.

        Returns:
            (is_allowed, requires_confirmation, reason_if_denied)
        """
        # Get permission setting
        permission = await self._get_permission(store_id, action_type)
        if not permission or not permission.enabled:
            return False, False, f"Action {action_type} is not enabled for this store"

        # Check limits if action involves money/quantities
        if action_data and not await self._check_limits(store_id, action_type, action_data):
            return False, False, f"Action exceeds configured limits"

        return True, permission.requires_confirmation, None

    async def _get_permission(self, store_id: UUID, action_type: ActionType) -> Optional[ActionPermission]:
        """Get permission setting for store and action type."""
        result = await self.db.execute(
            select(ActionPermission).where(
                and_(
                    ActionPermission.store_id == store_id,
                    ActionPermission.action_type == action_type
                )
            )
        )
        return result.scalar_one_or_none()

    async def _check_limits(self, store_id: UUID, action_type: ActionType, action_data: Dict) -> bool:
        """Check if action respects configured limits."""
        limits = await self._get_limits(store_id, action_type)

        for limit in limits:
            if limit.limit_type == LimitType.MAX_AMOUNT:
                amount = Decimal(str(action_data.get('amount', 0)))
                if amount > limit.limit_value:
                    return False

            elif limit.limit_type == LimitType.MAX_PERCENTAGE:
                percentage = Decimal(str(action_data.get('percentage', 0)))
                if percentage > limit.limit_value:
                    return False

            elif limit.limit_type == LimitType.TIME_WINDOW:
                # Check if too many actions in time window
                if not await self._check_time_window(store_id, action_type, limit):
                    return False

        return True

    async def _get_limits(self, store_id: UUID, action_type: ActionType) -> List[ActionLimit]:
        """Get all limits for store and action type."""
        result = await self.db.execute(
            select(ActionLimit).where(
                and_(
                    ActionLimit.store_id == store_id,
                    ActionLimit.action_type == action_type
                )
            )
        )
        return result.scalars().all()

    async def create_default_permissions(self, store_id: UUID) -> None:
        """Create default permission settings for new store."""
        default_permissions = [
            (ActionType.LOOKUP_ORDER, True, False),
            (ActionType.SEND_TRACKING, True, False),
            (ActionType.UPDATE_ADDRESS, False, True),
            (ActionType.CANCEL_ORDER, False, True),
            (ActionType.INITIATE_RETURN, False, True),
            (ActionType.PROCESS_REFUND, False, True),
            (ActionType.APPLY_DISCOUNT, False, True),
        ]

        for action_type, enabled, requires_confirmation in default_permissions:
            permission = ActionPermission(
                store_id=store_id,
                action_type=action_type,
                enabled=enabled,
                requires_confirmation=requires_confirmation
            )
            self.db.add(permission)

        await self.db.commit()
```

### 1.5 Permission Management API

**Location:** `apps/api/app/api/v1/permissions.py`

- [ ] `GET /api/v1/permissions` - List all permissions for store
- [ ] `PUT /api/v1/permissions/{action_type}` - Update permission
- [ ] `GET /api/v1/permissions/limits` - List limits
- [ ] `POST /api/v1/permissions/limits` - Create/update limit

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.deps import get_db, get_current_store
from app.models.store import Store
from app.services.permissions import PermissionService
from app.schemas.permissions import (
    ActionPermissionResponse, ActionPermissionUpdate,
    ActionLimitResponse, ActionLimitCreate, ActionType
)

router = APIRouter(prefix="/permissions", tags=["permissions"])

@router.get("/", response_model=List[ActionPermissionResponse])
async def list_permissions(
    store: Store = Depends(get_current_store),
    db: AsyncSession = Depends(get_db)
):
    """List all action permissions for the current store."""
    service = PermissionService(db)
    permissions = await service.get_store_permissions(store.id)
    return permissions

@router.put("/{action_type}", response_model=ActionPermissionResponse)
async def update_permission(
    action_type: ActionType,
    permission_update: ActionPermissionUpdate,
    store: Store = Depends(get_current_store),
    db: AsyncSession = Depends(get_db)
):
    """Update permission settings for a specific action type."""
    service = PermissionService(db)
    permission = await service.update_permission(
        store.id, action_type, permission_update
    )
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    return permission

@router.get("/limits", response_model=List[ActionLimitResponse])
async def list_limits(
    store: Store = Depends(get_current_store),
    db: AsyncSession = Depends(get_db)
):
    """List all action limits for the current store."""
    service = PermissionService(db)
    limits = await service.get_store_limits(store.id)
    return limits

@router.post("/limits", response_model=ActionLimitResponse)
async def create_limit(
    limit_data: ActionLimitCreate,
    store: Store = Depends(get_current_store),
    db: AsyncSession = Depends(get_db)
):
    """Create or update an action limit."""
    service = PermissionService(db)
    limit = await service.create_or_update_limit(store.id, limit_data)
    return limit
```

### 1.6 Dashboard Permission Settings

**Location:** `apps/web/app/dashboard/settings/actions/page.tsx`

- [ ] Create action permissions settings page
- [ ] Toggle switches for each action type
- [ ] Limit configuration forms
- [ ] Permission preview/testing

```typescript
'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface ActionPermission {
  id: string;
  action_type: string;
  enabled: boolean;
  requires_confirmation: boolean;
}

interface ActionLimit {
  id: string;
  action_type: string;
  limit_type: string;
  limit_value: number;
  time_window_hours?: number;
}

export default function ActionSettingsPage() {
  const [permissions, setPermissions] = useState<ActionPermission[]>([]);
  const [limits, setLimits] = useState<ActionLimit[]>([]);
  const [loading, setLoading] = useState(true);

  const actionLabels = {
    lookup_order: 'Look up order status',
    send_tracking: 'Send tracking information',
    update_address: 'Update shipping address',
    cancel_order: 'Cancel orders',
    initiate_return: 'Initiate returns',
    process_refund: 'Process refunds',
    apply_discount: 'Apply discounts'
  };

  useEffect(() => {
    fetchPermissions();
    fetchLimits();
  }, []);

  const fetchPermissions = async () => {
    try {
      const response = await fetch('/api/v1/permissions');
      const data = await response.json();
      setPermissions(data);
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
    }
  };

  const updatePermission = async (actionType: string, updates: Partial<ActionPermission>) => {
    try {
      const response = await fetch(`/api/v1/permissions/${actionType}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });

      if (response.ok) {
        await fetchPermissions();
      }
    } catch (error) {
      console.error('Failed to update permission:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Action Settings</h1>
        <p className="text-muted-foreground">
          Configure what actions your AI agent can perform
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Action Permissions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {permissions.map((permission) => (
            <div key={permission.id} className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <Label className="text-base font-medium">
                  {actionLabels[permission.action_type] || permission.action_type}
                </Label>
                <p className="text-sm text-muted-foreground">
                  {permission.requires_confirmation ? 'Requires customer confirmation' : 'Automatic'}
                </p>
              </div>
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <Label htmlFor={`confirm-${permission.action_type}`} className="text-sm">
                    Confirm
                  </Label>
                  <Switch
                    id={`confirm-${permission.action_type}`}
                    checked={permission.requires_confirmation}
                    onCheckedChange={(checked) =>
                      updatePermission(permission.action_type, { requires_confirmation: checked })
                    }
                  />
                </div>
                <Switch
                  checked={permission.enabled}
                  onCheckedChange={(checked) =>
                    updatePermission(permission.action_type, { enabled: checked })
                  }
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Action Limits</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="refund-limit">Maximum refund amount</Label>
                <Input
                  id="refund-limit"
                  type="number"
                  placeholder="100.00"
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="discount-limit">Maximum discount percentage</Label>
                <Input
                  id="discount-limit"
                  type="number"
                  placeholder="20"
                  className="mt-1"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## Files to Create/Modify

| File                                               | Action | Purpose                      |
| -------------------------------------------------- | ------ | ---------------------------- |
| `alembic/versions/xxx_action_permissions.py`       | Create | Database migration           |
| `app/models/permissions.py`                        | Create | SQLAlchemy models            |
| `app/schemas/permissions.py`                       | Create | Pydantic schemas             |
| `app/services/permissions.py`                      | Create | Permission checking logic    |
| `app/api/v1/permissions.py`                        | Create | Permission management API    |
| `app/models/store.py`                              | Modify | Add permission relationships |
| `apps/web/app/dashboard/settings/actions/page.tsx` | Create | Permission settings UI       |

---

## Dependencies

```toml
# No new Python dependencies required
```

```json
// No new Node.js dependencies required
```

---

## Testing

- [ ] Unit test: permission checking logic
- [ ] Unit test: limit validation (amount, percentage, time)
- [ ] Unit test: default permission creation
- [ ] Integration test: permission API endpoints
- [ ] E2E test: dashboard permission settings
- [ ] Test: permission inheritance and overrides

---

## Acceptance Criteria

1. Merchant can enable/disable each action type individually
2. Merchant can set confirmation requirements per action
3. Merchant can configure monetary and percentage limits
4. Default permissions are created for new stores
5. Permission checks are enforced before any action
6. Settings UI is intuitive and provides clear explanations
7. All permission changes are logged for audit

---

## Notes

- Start with conservative defaults (most actions disabled)
- Provide clear explanations of what each action does
- Consider adding action simulation/preview mode
- Plan for future permission inheritance (organization → store)
