# Phase 2: Core Action Tools

> **Parent:** [M5 Full Action Agent](../m5-action-agent.md)  
> **Duration:** 1.5 weeks  
> **Status:** Not Started  
> **Dependencies:** Phase 1 complete, Shopify Admin API access

---

## Goal

Implement the core action tools that integrate with Shopify's Admin API to perform real customer service actions like canceling orders, processing refunds, and initiating returns.

---

## Tasks

### 2.1 Shopify API Client Enhancement

**Location:** `apps/api/app/integrations/shopify/client.py`

- [ ] Add order management methods to existing Shopify client
- [ ] Implement error handling for action-specific API calls
- [ ] Add retry logic for transient failures
- [ ] Support webhook verification for order updates

```python
from typing import Dict, List, Optional
from decimal import Decimal
import httpx
from app.core.config import settings

class ShopifyActionClient:
    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.base_url = f"https://{shop_domain}.myshopify.com/admin/api/2024-01"

    async def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order details by ID."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/orders/{order_id}.json",
                headers={"X-Shopify-Access-Token": self.access_token}
            )
            if response.status_code == 200:
                return response.json()["order"]
            return None

    async def cancel_order(self, order_id: str, reason: str = "customer") -> Dict:
        """Cancel an order."""
        payload = {
            "order": {
                "id": order_id,
                "cancel_reason": reason
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/orders/{order_id}/cancel.json",
                headers={"X-Shopify-Access-Token": self.access_token},
                json=payload
            )
            response.raise_for_status()
            return response.json()["order"]

    async def create_refund(
        self,
        order_id: str,
        amount: Decimal,
        reason: str = "customer_request",
        line_items: Optional[List[Dict]] = None
    ) -> Dict:
        """Create a refund for an order."""
        refund_data = {
            "refund": {
                "currency": "USD",  # Should be dynamic based on order
                "notify": True,
                "note": reason,
                "shipping": {"full_refund": False},
                "refund_line_items": line_items or [],
                "transactions": [
                    {
                        "parent_id": None,  # Will be set to original transaction ID
                        "amount": str(amount),
                        "kind": "refund",
                        "gateway": "manual"
                    }
                ]
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/orders/{order_id}/refunds.json",
                headers={"X-Shopify-Access-Token": self.access_token},
                json=refund_data
            )
            response.raise_for_status()
            return response.json()["refund"]

    async def update_order(self, order_id: str, updates: Dict) -> Dict:
        """Update order details (e.g., shipping address)."""
        payload = {"order": updates}

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/orders/{order_id}.json",
                headers={"X-Shopify-Access-Token": self.access_token},
                json=payload
            )
            response.raise_for_status()
            return response.json()["order"]
```

### 2.2 Action Tool Base Class

**Location:** `apps/api/app/agents/tools/base.py`

- [ ] Create abstract base class for all action tools
- [ ] Define common interfaces and error handling
- [ ] Implement permission checking integration
- [ ] Add audit logging hooks

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from uuid import UUID
from pydantic import BaseModel

from app.services.permissions import PermissionService
from app.services.audit import AuditService
from app.schemas.permissions import ActionType

class ActionResult(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None

class BaseActionTool(ABC):
    """Base class for all action tools."""

    def __init__(
        self,
        permission_service: PermissionService,
        audit_service: AuditService
    ):
        self.permission_service = permission_service
        self.audit_service = audit_service

    @property
    @abstractmethod
    def action_type(self) -> ActionType:
        """The type of action this tool performs."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the action."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this action does."""
        pass

    async def execute(
        self,
        store_id: UUID,
        conversation_id: UUID,
        action_data: Dict[str, Any]
    ) -> ActionResult:
        """
        Execute the action with permission checking and audit logging.
        """
        # Check permissions
        is_allowed, requires_confirmation, denial_reason = await self.permission_service.check_action_permission(
            store_id=store_id,
            action_type=self.action_type,
            action_data=action_data
        )

        if not is_allowed:
            return ActionResult(
                success=False,
                error=denial_reason or f"Action {self.action_type} is not permitted"
            )

        # Log action attempt
        audit_id = await self.audit_service.log_action_attempt(
            store_id=store_id,
            conversation_id=conversation_id,
            action_type=self.action_type,
            action_data=action_data
        )

        try:
            if requires_confirmation:
                # Generate confirmation message
                confirmation_msg = await self._generate_confirmation_message(action_data)
                return ActionResult(
                    success=True,
                    requires_confirmation=True,
                    confirmation_message=confirmation_msg,
                    data={"audit_id": audit_id}
                )
            else:
                # Execute immediately
                result = await self._execute_action(store_id, action_data)

                # Log success
                await self.audit_service.log_action_success(audit_id, result)

                return ActionResult(success=True, data=result)

        except Exception as e:
            # Log failure
            await self.audit_service.log_action_failure(audit_id, str(e))
            return ActionResult(success=False, error=str(e))

    @abstractmethod
    async def _execute_action(self, store_id: UUID, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Implement the actual action logic."""
        pass

    @abstractmethod
    async def _generate_confirmation_message(self, action_data: Dict[str, Any]) -> str:
        """Generate a human-readable confirmation message."""
        pass
```

### 2.3 Order Cancellation Tool

**Location:** `apps/api/app/agents/tools/cancel_order.py`

- [ ] Implement order cancellation with Shopify API
- [ ] Validate order can be cancelled (not fulfilled)
- [ ] Generate clear confirmation messages
- [ ] Handle partial cancellations

```python
from typing import Dict, Any
from uuid import UUID
from decimal import Decimal

from app.agents.tools.base import BaseActionTool, ActionResult
from app.schemas.permissions import ActionType
from app.integrations.shopify.client import ShopifyActionClient
from app.services.store import StoreService

class CancelOrderTool(BaseActionTool):
    """Tool for canceling orders."""

    def __init__(self, permission_service, audit_service, store_service: StoreService):
        super().__init__(permission_service, audit_service)
        self.store_service = store_service

    @property
    def action_type(self) -> ActionType:
        return ActionType.CANCEL_ORDER

    @property
    def name(self) -> str:
        return "Cancel Order"

    @property
    def description(self) -> str:
        return "Cancel an unfulfilled order and process refund if payment was captured"

    async def _execute_action(self, store_id: UUID, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute order cancellation."""
        order_id = action_data["order_id"]
        reason = action_data.get("reason", "customer_request")

        # Get store's Shopify credentials
        store = await self.store_service.get_store(store_id)
        shopify_client = ShopifyActionClient(
            shop_domain=store.shopify_domain,
            access_token=store.shopify_access_token
        )

        # Get order details first
        order = await shopify_client.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Check if order can be cancelled
        if order["fulfillment_status"] == "fulfilled":
            raise ValueError("Cannot cancel fulfilled orders")

        # Cancel the order
        cancelled_order = await shopify_client.cancel_order(order_id, reason)

        return {
            "order_id": order_id,
            "status": cancelled_order["cancel_reason"],
            "refund_amount": cancelled_order.get("total_price", "0"),
            "cancelled_at": cancelled_order["cancelled_at"]
        }

    async def _generate_confirmation_message(self, action_data: Dict[str, Any]) -> str:
        """Generate confirmation message for order cancellation."""
        order_id = action_data["order_id"]

        # You might want to fetch order details to show amount
        return (
            f"I can cancel order #{order_id} for you right now. "
            f"If payment was already captured, your refund will be processed "
            f"within 3-5 business days. Should I proceed with the cancellation?"
        )
```

### 2.4 Refund Processing Tool

**Location:** `apps/api/app/agents/tools/process_refund.py`

- [ ] Implement partial and full refunds
- [ ] Validate refund amounts against limits
- [ ] Support line-item specific refunds
- [ ] Handle different payment gateways

```python
from typing import Dict, Any, List, Optional
from uuid import UUID
from decimal import Decimal

from app.agents.tools.base import BaseActionTool
from app.schemas.permissions import ActionType
from app.integrations.shopify.client import ShopifyActionClient
from app.services.store import StoreService

class ProcessRefundTool(BaseActionTool):
    """Tool for processing refunds."""

    def __init__(self, permission_service, audit_service, store_service: StoreService):
        super().__init__(permission_service, audit_service)
        self.store_service = store_service

    @property
    def action_type(self) -> ActionType:
        return ActionType.PROCESS_REFUND

    @property
    def name(self) -> str:
        return "Process Refund"

    @property
    def description(self) -> str:
        return "Process full or partial refunds for orders"

    async def _execute_action(self, store_id: UUID, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute refund processing."""
        order_id = action_data["order_id"]
        amount = Decimal(str(action_data["amount"]))
        reason = action_data.get("reason", "customer_request")
        line_items = action_data.get("line_items")

        # Get store's Shopify credentials
        store = await self.store_service.get_store(store_id)
        shopify_client = ShopifyActionClient(
            shop_domain=store.shopify_domain,
            access_token=store.shopify_access_token
        )

        # Get order details
        order = await shopify_client.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Validate refund amount
        order_total = Decimal(order["total_price"])
        if amount > order_total:
            raise ValueError(f"Refund amount ${amount} exceeds order total ${order_total}")

        # Process the refund
        refund = await shopify_client.create_refund(
            order_id=order_id,
            amount=amount,
            reason=reason,
            line_items=line_items
        )

        return {
            "refund_id": refund["id"],
            "order_id": order_id,
            "amount": str(amount),
            "currency": order["currency"],
            "processed_at": refund["processed_at"],
            "note": reason
        }

    async def _generate_confirmation_message(self, action_data: Dict[str, Any]) -> str:
        """Generate confirmation message for refund."""
        order_id = action_data["order_id"]
        amount = action_data["amount"]

        return (
            f"I can process a ${amount} refund for order #{order_id}. "
            f"The refund will appear on your original payment method within "
            f"3-5 business days. Should I proceed with this refund?"
        )
```

### 2.5 Return Initiation Tool

**Location:** `apps/api/app/agents/tools/initiate_return.py`

- [ ] Create return authorization
- [ ] Generate return shipping labels (if configured)
- [ ] Send return instructions to customer
- [ ] Track return status

```python
from typing import Dict, Any
from uuid import UUID

from app.agents.tools.base import BaseActionTool
from app.schemas.permissions import ActionType
from app.integrations.shopify.client import ShopifyActionClient
from app.services.store import StoreService

class InitiateReturnTool(BaseActionTool):
    """Tool for initiating product returns."""

    def __init__(self, permission_service, audit_service, store_service: StoreService):
        super().__init__(permission_service, audit_service)
        self.store_service = store_service

    @property
    def action_type(self) -> ActionType:
        return ActionType.INITIATE_RETURN

    @property
    def name(self) -> str:
        return "Initiate Return"

    @property
    def description(self) -> str:
        return "Start the return process for products"

    async def _execute_action(self, store_id: UUID, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute return initiation."""
        order_id = action_data["order_id"]
        line_items = action_data["line_items"]  # Items to return
        reason = action_data.get("reason", "customer_request")

        # Get store's Shopify credentials
        store = await self.store_service.get_store(store_id)
        shopify_client = ShopifyActionClient(
            shop_domain=store.shopify_domain,
            access_token=store.shopify_access_token
        )

        # Get order details
        order = await shopify_client.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Validate return eligibility
        if order["fulfillment_status"] != "fulfilled":
            raise ValueError("Can only return fulfilled orders")

        # Create return record (this might be a custom implementation)
        # For now, we'll use Shopify's draft order or custom tracking

        return_data = {
            "return_id": f"RET-{order_id}-{len(line_items)}",
            "order_id": order_id,
            "items": line_items,
            "reason": reason,
            "status": "initiated",
            "return_address": store.return_address,  # Store's return address
            "instructions": self._generate_return_instructions(store, order_id)
        }

        return return_data

    async def _generate_confirmation_message(self, action_data: Dict[str, Any]) -> str:
        """Generate confirmation message for return."""
        order_id = action_data["order_id"]
        items_count = len(action_data.get("line_items", []))

        return (
            f"I can start the return process for {items_count} item(s) "
            f"from order #{order_id}. You'll receive return instructions "
            f"and a prepaid shipping label via email. Should I proceed?"
        )

    def _generate_return_instructions(self, store, order_id: str) -> str:
        """Generate return instructions for customer."""
        return f"""
        Return Instructions for Order #{order_id}:

        1. Pack items securely in original packaging if possible
        2. Include this return authorization in the package
        3. Use the prepaid shipping label provided
        4. Drop off at any authorized shipping location

        Return Address:
        {store.name}
        {store.return_address}

        Questions? Contact us at {store.support_email}
        """
```

### 2.6 Discount Application Tool

**Location:** `apps/api/app/agents/tools/apply_discount.py`

- [ ] Apply percentage or fixed amount discounts
- [ ] Validate discount limits
- [ ] Create discount codes for future orders
- [ ] Handle order modifications

```python
from typing import Dict, Any
from uuid import UUID
from decimal import Decimal

from app.agents.tools.base import BaseActionTool
from app.schemas.permissions import ActionType
from app.integrations.shopify.client import ShopifyActionClient
from app.services.store import StoreService

class ApplyDiscountTool(BaseActionTool):
    """Tool for applying discounts to orders."""

    def __init__(self, permission_service, audit_service, store_service: StoreService):
        super().__init__(permission_service, audit_service)
        self.store_service = store_service

    @property
    def action_type(self) -> ActionType:
        return ActionType.APPLY_DISCOUNT

    @property
    def name(self) -> str:
        return "Apply Discount"

    @property
    def description(self) -> str:
        return "Apply discounts to orders or create discount codes"

    async def _execute_action(self, store_id: UUID, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute discount application."""
        discount_type = action_data["type"]  # "percentage" or "fixed_amount"
        discount_value = Decimal(str(action_data["value"]))
        order_id = action_data.get("order_id")  # For existing orders
        reason = action_data.get("reason", "customer_service")

        # Get store's Shopify credentials
        store = await self.store_service.get_store(store_id)
        shopify_client = ShopifyActionClient(
            shop_domain=store.shopify_domain,
            access_token=store.shopify_access_token
        )

        if order_id:
            # Apply discount to existing order (if possible)
            # Note: Shopify doesn't allow modifying completed orders
            # This would typically create a partial refund instead
            order = await shopify_client.get_order(order_id)
            if not order:
                raise ValueError(f"Order {order_id} not found")

            if order["financial_status"] == "paid":
                # Calculate discount amount
                order_total = Decimal(order["total_price"])
                if discount_type == "percentage":
                    discount_amount = order_total * (discount_value / 100)
                else:
                    discount_amount = discount_value

                # Process as refund
                refund = await shopify_client.create_refund(
                    order_id=order_id,
                    amount=discount_amount,
                    reason=f"Discount applied: {reason}"
                )

                return {
                    "type": "refund_discount",
                    "order_id": order_id,
                    "discount_amount": str(discount_amount),
                    "refund_id": refund["id"]
                }
        else:
            # Create discount code for future use
            # This would use Shopify's Price Rules API
            discount_code = f"SUPPORT{store_id.hex[:8].upper()}"

            # Implementation would create price rule and discount code
            # For now, return the code details
            return {
                "type": "discount_code",
                "code": discount_code,
                "discount_type": discount_type,
                "discount_value": str(discount_value),
                "expires_at": None  # Could set expiration
            }

    async def _generate_confirmation_message(self, action_data: Dict[str, Any]) -> str:
        """Generate confirmation message for discount."""
        discount_type = action_data["type"]
        discount_value = action_data["value"]
        order_id = action_data.get("order_id")

        if discount_type == "percentage":
            discount_text = f"{discount_value}% discount"
        else:
            discount_text = f"${discount_value} discount"

        if order_id:
            return (
                f"I can apply a {discount_text} to order #{order_id} "
                f"by processing a partial refund. Should I proceed?"
            )
        else:
            return (
                f"I can create a {discount_text} code for your next order. "
                f"Should I generate this discount code for you?"
            )
```

### 2.7 Tool Registry

**Location:** `apps/api/app/agents/tools/registry.py`

- [ ] Register all action tools
- [ ] Provide tool discovery for LangGraph
- [ ] Handle tool initialization with dependencies

```python
from typing import Dict, Type, List
from app.agents.tools.base import BaseActionTool
from app.agents.tools.cancel_order import CancelOrderTool
from app.agents.tools.process_refund import ProcessRefundTool
from app.agents.tools.initiate_return import InitiateReturnTool
from app.agents.tools.apply_discount import ApplyDiscountTool
from app.services.permissions import PermissionService
from app.services.audit import AuditService
from app.services.store import StoreService

class ActionToolRegistry:
    """Registry for all action tools."""

    def __init__(
        self,
        permission_service: PermissionService,
        audit_service: AuditService,
        store_service: StoreService
    ):
        self.permission_service = permission_service
        self.audit_service = audit_service
        self.store_service = store_service
        self._tools: Dict[str, BaseActionTool] = {}
        self._initialize_tools()

    def _initialize_tools(self):
        """Initialize all available tools."""
        tools = [
            CancelOrderTool,
            ProcessRefundTool,
            InitiateReturnTool,
            ApplyDiscountTool
        ]

        for tool_class in tools:
            tool = tool_class(
                self.permission_service,
                self.audit_service,
                self.store_service
            )
            self._tools[tool.action_type.value] = tool

    def get_tool(self, action_type: str) -> BaseActionTool:
        """Get tool by action type."""
        if action_type not in self._tools:
            raise ValueError(f"Unknown action type: {action_type}")
        return self._tools[action_type]

    def list_tools(self) -> List[BaseActionTool]:
        """List all available tools."""
        return list(self._tools.values())

    def get_tool_descriptions(self) -> Dict[str, str]:
        """Get descriptions of all tools for LLM context."""
        return {
            action_type: tool.description
            for action_type, tool in self._tools.items()
        }
```

---

## Files to Create/Modify

| File                                  | Action | Purpose                              |
| ------------------------------------- | ------ | ------------------------------------ |
| `app/integrations/shopify/client.py`  | Modify | Add action methods to Shopify client |
| `app/agents/__init__.py`              | Create | Package init                         |
| `app/agents/tools/__init__.py`        | Create | Tools package init                   |
| `app/agents/tools/base.py`            | Create | Base action tool class               |
| `app/agents/tools/cancel_order.py`    | Create | Order cancellation tool              |
| `app/agents/tools/process_refund.py`  | Create | Refund processing tool               |
| `app/agents/tools/initiate_return.py` | Create | Return initiation tool               |
| `app/agents/tools/apply_discount.py`  | Create | Discount application tool            |
| `app/agents/tools/registry.py`        | Create | Tool registry and discovery          |
| `app/services/audit.py`               | Create | Audit logging service                |

---

## Dependencies

```toml
# Add to pyproject.toml
httpx = "^0.27"  # Already included for API calls
```

---

## Testing

- [ ] Unit test: each action tool individually
- [ ] Unit test: permission checking integration
- [ ] Unit test: Shopify API error handling
- [ ] Integration test: full action flow with mocked Shopify API
- [ ] Test: action limits and validation
- [ ] Test: audit logging for all actions

---

## Acceptance Criteria

1. Each action tool can execute its specific Shopify API operation
2. Permission checking is enforced before any action execution
3. All actions are logged in the audit trail
4. Error handling provides clear feedback for failures
5. Confirmation messages are clear and informative
6. Tools respect configured limits (amounts, percentages)
7. Shopify API errors are handled gracefully

---

## Notes

- Start with order cancellation as it's the most straightforward
- Test thoroughly with Shopify development store
- Consider rate limiting for Shopify API calls
- Plan for webhook handling to track action results
- Implement idempotency for action execution
