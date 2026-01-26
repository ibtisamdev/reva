# Phase 3: Marketing Integrations

> **Parent:** [M4 Cart Recovery Agent](../m4-cart-recovery.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 2 complete (recovery engine)

---

## Goal

Integrate with existing marketing tools to coordinate cart recovery efforts, avoid duplicate messaging, and provide comprehensive attribution tracking through email delivery and analytics platforms.

---

## Tasks

### 3.1 Email Delivery via Resend

**Location:** `apps/api/app/services/email.py`

- [ ] Integrate Resend API for email delivery
- [ ] Create responsive email templates
- [ ] Implement email tracking (opens, clicks, bounces)
- [ ] Add unsubscribe handling
- [ ] Support email personalization with cart data

**Email service implementation:**

```python
import httpx
from jinja2 import Environment, FileSystemLoader
from app.core.config import settings

class EmailService:
    def __init__(self):
        self.client = httpx.AsyncClient()
        self.base_url = "https://api.resend.com"
        self.template_env = Environment(
            loader=FileSystemLoader("app/templates/email")
        )

    async def send_recovery_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        cart: Cart,
        sequence: RecoverySequence
    ) -> dict:
        """Send cart recovery email via Resend."""

        # Generate tracking URLs
        tracking_params = {
            "utm_source": "reva",
            "utm_medium": "email",
            "utm_campaign": "cart_recovery",
            "utm_content": sequence.current_step,
            "sequence_id": str(sequence.id)
        }

        # Render email template
        template = self.template_env.get_template("cart_recovery.html")
        html_content = template.render(
            cart=cart,
            body=body,
            tracking_params=tracking_params,
            unsubscribe_url=self._generate_unsubscribe_url(cart.customer_email)
        )

        # Send via Resend
        payload = {
            "from": f"{cart.store.name} <noreply@{cart.store.domain}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
            "tags": [
                {"name": "type", "value": "cart_recovery"},
                {"name": "step", "value": sequence.current_step},
                {"name": "store_id", "value": str(cart.store_id)}
            ]
        }

        response = await self.client.post(
            f"{self.base_url}/emails",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json"
            }
        )

        if response.status_code == 200:
            result = response.json()

            # Track email sent
            await self._track_email_sent(sequence, result["id"])

            return result
        else:
            raise Exception(f"Email send failed: {response.text}")

    def _generate_unsubscribe_url(self, email: str) -> str:
        """Generate unsubscribe URL for email."""
        token = self._create_unsubscribe_token(email)
        return f"{settings.WEB_BASE_URL}/unsubscribe?token={token}"
```

### 3.2 Klaviyo Integration

**Location:** `apps/api/app/integrations/klaviyo.py`

- [ ] Connect to Klaviyo API to check existing flows
- [ ] Detect if Klaviyo already sent recovery email
- [ ] Coordinate timing to avoid duplicate messages
- [ ] Sync recovery events to Klaviyo for unified reporting

**Klaviyo coordination:**

```python
import httpx
from datetime import datetime, timedelta

class KlaviyoIntegration:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient()
        self.base_url = "https://a.klaviyo.com/api"

    async def check_existing_recovery_emails(
        self,
        email: str,
        cart_token: str,
        hours_back: int = 24
    ) -> list[dict]:
        """Check if Klaviyo sent recovery emails recently."""

        # Get events for this email in the last 24 hours
        since = datetime.utcnow() - timedelta(hours=hours_back)

        params = {
            "filter": f'equals(email,"{email}") and greater-than(datetime,"{since.isoformat()}")',
            "fields[event]": "event_name,datetime,event_properties"
        }

        response = await self.client.get(
            f"{self.base_url}/events/",
            params=params,
            headers={"Authorization": f"Klaviyo-API-Key {self.api_key}"}
        )

        if response.status_code == 200:
            events = response.json().get("data", [])

            # Filter for cart recovery related events
            recovery_events = [
                event for event in events
                if "abandoned" in event.get("attributes", {}).get("event_name", "").lower()
                or "cart" in event.get("attributes", {}).get("event_name", "").lower()
            ]

            return recovery_events

        return []

    async def should_skip_email(
        self,
        cart: Cart,
        sequence_step: str
    ) -> tuple[bool, str]:
        """Determine if we should skip sending email due to Klaviyo activity."""

        if not cart.customer_email:
            return False, ""

        # Check recent Klaviyo activity
        recent_emails = await self.check_existing_recovery_emails(
            cart.customer_email,
            cart.shopify_cart_id
        )

        if recent_emails:
            latest_email = max(recent_emails, key=lambda x: x["attributes"]["datetime"])
            return True, f"Klaviyo sent recovery email at {latest_email['attributes']['datetime']}"

        return False, ""

    async def sync_recovery_event(self, sequence: RecoverySequence, event_type: str):
        """Send recovery event to Klaviyo for unified tracking."""

        if not sequence.cart.customer_email:
            return

        event_data = {
            "data": {
                "type": "event",
                "attributes": {
                    "profile": {"email": sequence.cart.customer_email},
                    "metric": {"name": f"Reva Cart Recovery {event_type.title()}"},
                    "properties": {
                        "cart_id": sequence.cart.shopify_cart_id,
                        "sequence_type": sequence.sequence_type,
                        "step": sequence.current_step,
                        "cart_value": float(sequence.cart.total_price),
                        "recovery_source": "reva_ai"
                    },
                    "time": datetime.utcnow().isoformat()
                }
            }
        }

        await self.client.post(
            f"{self.base_url}/events/",
            json=event_data,
            headers={"Authorization": f"Klaviyo-API-Key {self.api_key}"}
        )
```

### 3.3 Google Analytics 4 Tracking

**Location:** `apps/api/app/services/analytics.py`

- [ ] Implement GA4 Measurement Protocol
- [ ] Track recovery email events (sent, opened, clicked)
- [ ] Attribute recovered purchases to Reva
- [ ] Generate UTM parameters for email links
- [ ] Create custom GA4 events for recovery funnel

**GA4 tracking implementation:**

```python
import httpx
from urllib.parse import urlencode

class GA4Tracker:
    def __init__(self, measurement_id: str, api_secret: str):
        self.measurement_id = measurement_id
        self.api_secret = api_secret
        self.client = httpx.AsyncClient()
        self.endpoint = f"https://www.google-analytics.com/mp/collect"

    async def track_recovery_email_sent(
        self,
        cart: Cart,
        sequence: RecoverySequence,
        client_id: str = None
    ):
        """Track recovery email sent event in GA4."""

        client_id = client_id or self._generate_client_id(cart.customer_email)

        event_data = {
            "client_id": client_id,
            "events": [{
                "name": "recovery_email_sent",
                "parameters": {
                    "email_step": sequence.current_step,
                    "cart_value": float(cart.total_price),
                    "currency": cart.currency,
                    "sequence_type": sequence.sequence_type,
                    "store_id": str(cart.store_id),
                    "custom_parameter_1": "reva_recovery"
                }
            }]
        }

        await self._send_event(event_data)

    async def track_recovery_conversion(
        self,
        cart: Cart,
        order_value: float,
        sequence: RecoverySequence
    ):
        """Track successful cart recovery conversion."""

        client_id = self._generate_client_id(cart.customer_email)

        event_data = {
            "client_id": client_id,
            "events": [{
                "name": "purchase",
                "parameters": {
                    "transaction_id": f"recovery_{cart.shopify_cart_id}",
                    "value": order_value,
                    "currency": cart.currency,
                    "source": "reva_recovery",
                    "medium": "email",
                    "campaign": "cart_recovery",
                    "content": sequence.current_step
                }
            }]
        }

        await self._send_event(event_data)

    def generate_tracking_url(
        self,
        base_url: str,
        sequence: RecoverySequence,
        action: str = "click"
    ) -> str:
        """Generate URL with UTM parameters for tracking."""

        utm_params = {
            "utm_source": "reva",
            "utm_medium": "email",
            "utm_campaign": "cart_recovery",
            "utm_content": f"{sequence.current_step}_{action}",
            "utm_term": sequence.sequence_type
        }

        return f"{base_url}?{urlencode(utm_params)}"

    async def _send_event(self, event_data: dict):
        """Send event to GA4 Measurement Protocol."""

        params = {
            "measurement_id": self.measurement_id,
            "api_secret": self.api_secret
        }

        response = await self.client.post(
            self.endpoint,
            params=params,
            json=event_data
        )

        if response.status_code != 204:
            # GA4 returns 204 for successful events
            print(f"GA4 tracking failed: {response.status_code} {response.text}")
```

### 3.4 On-Site Recovery Popup

**Location:** `apps/widget/src/components/RecoveryPopup.tsx`

- [ ] Detect returning visitors with abandoned carts
- [ ] Show personalized recovery popup
- [ ] Integrate with existing chat widget
- [ ] Track popup interactions
- [ ] Support popup dismissal and frequency capping

**Recovery popup component:**

```typescript
import { useState, useEffect } from 'preact/hooks';
import { trackEvent } from '../utils/analytics';

interface RecoveryPopupProps {
  cartId: string;
  cartItems: CartItem[];
  onRecover: () => void;
  onDismiss: () => void;
}

export function RecoveryPopup({ cartId, cartItems, onRecover, onDismiss }: RecoveryPopupProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Show popup after 30 seconds on page
    const timer = setTimeout(() => {
      setIsVisible(true);
      trackEvent('recovery_popup_shown', {
        cart_id: cartId,
        cart_value: cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0)
      });
    }, 30000);

    return () => clearTimeout(timer);
  }, []);

  const handleRecover = () => {
    trackEvent('recovery_popup_clicked', { cart_id: cartId });
    onRecover();
    setIsVisible(false);
  };

  const handleDismiss = () => {
    trackEvent('recovery_popup_dismissed', { cart_id: cartId });
    onDismiss();
    setIsVisible(false);

    // Don't show again for 24 hours
    localStorage.setItem(`recovery_dismissed_${cartId}`, Date.now().toString());
  };

  if (!isVisible) return null;

  return (
    <div className="recovery-popup-overlay">
      <div className="recovery-popup">
        <div className="recovery-popup-header">
          <h3>Still thinking about your cart?</h3>
          <button onClick={handleDismiss} className="close-button">×</button>
        </div>

        <div className="recovery-popup-content">
          <p>You left some great items in your cart:</p>

          <div className="cart-items">
            {cartItems.slice(0, 3).map(item => (
              <div key={item.id} className="cart-item">
                <img src={item.image} alt={item.title} />
                <span>{item.title}</span>
                <span>${item.price}</span>
              </div>
            ))}
          </div>

          <p>Complete your purchase now and get free shipping!</p>

          <div className="recovery-popup-actions">
            <button onClick={handleRecover} className="recover-button">
              Complete Purchase
            </button>
            <button onClick={handleDismiss} className="dismiss-button">
              Maybe Later
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

### 3.5 Webhook Integration Coordination

**Location:** `apps/api/app/services/integration_coordinator.py`

- [ ] Check all marketing integrations before sending
- [ ] Coordinate timing across platforms
- [ ] Handle integration failures gracefully
- [ ] Provide fallback when integrations are down

**Integration coordination:**

```python
from app.integrations.klaviyo import KlaviyoIntegration
from app.services.analytics import GA4Tracker

class IntegrationCoordinator:
    def __init__(self, store: Store):
        self.store = store
        self.klaviyo = self._init_klaviyo() if store.klaviyo_api_key else None
        self.ga4 = self._init_ga4() if store.ga4_measurement_id else None

    async def should_send_recovery_email(
        self,
        cart: Cart,
        sequence_step: str
    ) -> tuple[bool, str]:
        """Check all integrations to determine if email should be sent."""

        # Check Klaviyo for existing recovery emails
        if self.klaviyo:
            skip_klaviyo, reason = await self.klaviyo.should_skip_email(cart, sequence_step)
            if skip_klaviyo:
                return False, f"Klaviyo coordination: {reason}"

        # Check customer preferences (unsubscribed, frequency caps)
        if await self._check_customer_preferences(cart.customer_email):
            return False, "Customer preferences: unsubscribed or frequency limit"

        # Check store sending limits
        if await self._check_store_limits(cart.store_id):
            return False, "Store sending limits reached"

        return True, "All checks passed"

    async def track_email_sent(self, cart: Cart, sequence: RecoverySequence):
        """Track email sent across all analytics platforms."""

        # Track in GA4
        if self.ga4:
            try:
                await self.ga4.track_recovery_email_sent(cart, sequence)
            except Exception as e:
                print(f"GA4 tracking failed: {e}")

        # Sync to Klaviyo
        if self.klaviyo:
            try:
                await self.klaviyo.sync_recovery_event(sequence, "email_sent")
            except Exception as e:
                print(f"Klaviyo sync failed: {e}")

    async def track_recovery_conversion(
        self,
        cart: Cart,
        order_value: float,
        sequence: RecoverySequence
    ):
        """Track successful recovery across all platforms."""

        # Track in GA4
        if self.ga4:
            await self.ga4.track_recovery_conversion(cart, order_value, sequence)

        # Sync to Klaviyo
        if self.klaviyo:
            await self.klaviyo.sync_recovery_event(sequence, "conversion")
```

### 3.6 Recovery Dashboard

**Location:** `apps/web/src/app/(dashboard)/recovery/page.tsx`

- [ ] Display active recovery sequences
- [ ] Show recovery performance metrics
- [ ] Provide sequence management controls
- [ ] Visualize recovery funnel analytics

**Recovery dashboard component:**

```typescript
'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface RecoverySequence {
  id: string;
  cart: {
    total_price: number;
    customer_email: string;
    items: CartItem[];
  };
  sequence_type: string;
  current_step: string;
  steps_completed: string[];
  started_at: string;
}

export default function RecoveryPage() {
  const [sequences, setSequences] = useState<RecoverySequence[]>([]);
  const [analytics, setAnalytics] = useState({
    recovery_rate: 0,
    total_sequences: 0,
    recovered_revenue: 0
  });

  useEffect(() => {
    fetchRecoveryData();
  }, []);

  const fetchRecoveryData = async () => {
    const [sequencesRes, analyticsRes] = await Promise.all([
      fetch('/api/v1/recovery/sequences'),
      fetch('/api/v1/recovery/analytics')
    ]);

    setSequences(await sequencesRes.json());
    setAnalytics(await analyticsRes.json());
  };

  const stopSequence = async (sequenceId: string) => {
    await fetch(`/api/v1/recovery/sequences/${sequenceId}/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: 'manual_stop' })
    });

    fetchRecoveryData();
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Cart Recovery</h1>
      </div>

      {/* Analytics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recovery Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.recovery_rate.toFixed(1)}%</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active Sequences</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{sequences.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recovered Revenue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${analytics.recovered_revenue.toFixed(2)}</div>
          </CardContent>
        </Card>
      </div>

      {/* Active Sequences */}
      <Card>
        <CardHeader>
          <CardTitle>Active Recovery Sequences</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {sequences.map(sequence => (
              <div key={sequence.id} className="border rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-medium">{sequence.cart.customer_email}</div>
                    <div className="text-sm text-gray-600">
                      Cart Value: ${sequence.cart.total_price}
                    </div>
                    <div className="text-sm text-gray-600">
                      Started: {new Date(sequence.started_at).toLocaleDateString()}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{sequence.current_step}</Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => stopSequence(sequence.id)}
                    >
                      Stop
                    </Button>
                  </div>
                </div>

                <div className="mt-2">
                  <div className="text-sm text-gray-600">Progress:</div>
                  <div className="flex gap-1 mt-1">
                    {['popup_1h', 'email_2h', 'email_24h', 'email_48h', 'email_72h'].map(step => (
                      <div
                        key={step}
                        className={`w-4 h-4 rounded ${
                          sequence.steps_completed.includes(step)
                            ? 'bg-green-500'
                            : sequence.current_step === step
                            ? 'bg-blue-500'
                            : 'bg-gray-200'
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## Files to Create/Modify

| File                                             | Action | Purpose                     |
| ------------------------------------------------ | ------ | --------------------------- |
| `app/services/email.py`                          | Create | Resend email integration    |
| `app/integrations/klaviyo.py`                    | Create | Klaviyo API coordination    |
| `app/services/analytics.py`                      | Modify | Add GA4 tracking            |
| `app/services/integration_coordinator.py`        | Create | Coordinate all integrations |
| `app/templates/email/cart_recovery.html`         | Create | Email template              |
| `apps/widget/src/components/RecoveryPopup.tsx`   | Create | On-site recovery popup      |
| `apps/web/src/app/(dashboard)/recovery/page.tsx` | Create | Recovery dashboard          |
| `app/api/v1/unsubscribe.py`                      | Create | Unsubscribe handling        |

---

## Dependencies

```toml
# Add to pyproject.toml
httpx = "^0.27"         # API calls to integrations
jinja2 = "^3.1"         # Email templating
```

---

## Testing

- [ ] Unit test: Resend email delivery
- [ ] Unit test: Klaviyo coordination logic
- [ ] Unit test: GA4 event tracking
- [ ] Integration test: full recovery flow with tracking
- [ ] Test: unsubscribe handling
- [ ] Test: popup display and interactions
- [ ] Test: dashboard data accuracy

---

## Acceptance Criteria

1. Emails are delivered successfully via Resend with tracking
2. Klaviyo integration prevents duplicate recovery emails
3. GA4 accurately tracks recovery attribution and conversions
4. On-site popup shows for returning visitors with abandoned carts
5. Recovery dashboard displays real-time sequence status
6. Unsubscribe links work and are respected
7. All integrations handle failures gracefully

---

## Notes

- Start with Resend integration, add other platforms iteratively
- Monitor email deliverability rates and adjust sending patterns
- Consider A/B testing popup timing and messaging
- Implement proper error handling for all external API calls
