# Phase 4: Developer Portal

> **Parent:** [M8 Developer Platform](../m8-developer-platform.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 1 (Public API), Phase 2 (Webhooks), Phase 3 (Custom Tools)

---

## Goal

Create a comprehensive developer portal with API documentation, key management, usage analytics, SDK downloads, and a sandbox environment for testing integrations.

---

## Tasks

### 4.1 Developer Portal Frontend

**Location:** `apps/web/app/developer/`

- [ ] Create developer portal layout and navigation:

  ```tsx
  // apps/web/app/developer/layout.tsx
  export default function DeveloperLayout({ children }: { children: React.ReactNode }) {
    return (
      <div className="min-h-screen bg-gray-50">
        <DeveloperNavbar />
        <div className="flex">
          <DeveloperSidebar />
          <main className="flex-1 p-6">{children}</main>
        </div>
      </div>
    );
  }
  ```

- [ ] Developer dashboard overview:

  ```tsx
  // apps/web/app/developer/page.tsx
  export default function DeveloperDashboard() {
    return (
      <div className="space-y-6">
        <DeveloperWelcome />
        <QuickStartGuide />
        <APIUsageOverview />
        <RecentActivity />
        <PopularEndpoints />
      </div>
    );
  }
  ```

- [ ] Navigation structure:
  ```
  /developer/
  ├── overview/          # Dashboard
  ├── api-keys/          # API key management
  ├── webhooks/          # Webhook management
  ├── tools/             # Custom tools
  ├── analytics/         # Usage analytics
  ├── docs/              # API documentation
  ├── sdks/              # SDK downloads
  └── sandbox/           # Testing environment
  ```

### 4.2 API Key Management Interface

**Location:** `apps/web/app/developer/api-keys/`

- [ ] API key listing and management:

  ```tsx
  // apps/web/app/developer/api-keys/page.tsx
  export default function APIKeysPage() {
    const { data: apiKeys } = useAPIKeys();

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">API Keys</h1>
          <CreateAPIKeyButton />
        </div>

        <APIKeysList keys={apiKeys} />
        <APIKeyUsageChart />
      </div>
    );
  }
  ```

- [ ] API key creation modal:

  ```tsx
  // components/developer/CreateAPIKeyModal.tsx
  export function CreateAPIKeyModal() {
    return (
      <Dialog>
        <DialogContent>
          <form onSubmit={handleCreateKey}>
            <div className="space-y-4">
              <Input label="Key Name" placeholder="My Integration Key" required />

              <ScopeSelector
                scopes={availableScopes}
                selected={selectedScopes}
                onChange={setSelectedScopes}
              />

              <RateLimitSelector
                tier={organization.plan}
                selected={rateLimit}
                onChange={setRateLimit}
              />
            </div>

            <DialogFooter>
              <Button type="submit">Create API Key</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    );
  }
  ```

- [ ] API key display with security:
  ```tsx
  // components/developer/APIKeyDisplay.tsx
  export function APIKeyDisplay({ apiKey }: { apiKey: string }) {
    const [isVisible, setIsVisible] = useState(false);

    return (
      <div className="rounded-lg bg-gray-100 p-4">
        <div className="flex items-center justify-between">
          <code className="font-mono">
            {isVisible ? apiKey : '••••••••••••••••••••••••••••••••'}
          </code>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => setIsVisible(!isVisible)}>
              {isVisible ? <EyeOff /> : <Eye />}
            </Button>
            <CopyButton value={apiKey} />
          </div>
        </div>

        <Alert className="mt-4">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            This is the only time you'll see this key. Store it securely.
          </AlertDescription>
        </Alert>
      </div>
    );
  }
  ```

### 4.3 Interactive API Documentation

**Location:** `apps/web/app/developer/docs/`

- [ ] Auto-generated OpenAPI documentation:

  ```tsx
  // apps/web/app/developer/docs/page.tsx
  export default function APIDocs() {
    return (
      <div className="grid h-full grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <APIEndpointsList />
          <EndpointDetails />
        </div>

        <div className="rounded-lg bg-gray-900 p-6 text-white">
          <APIPlayground />
        </div>
      </div>
    );
  }
  ```

- [ ] Interactive API playground:
  ```tsx
  // components/developer/APIPlayground.tsx
  export function APIPlayground() {
    const [endpoint, setEndpoint] = useState('/api/v1/conversations');
    const [method, setMethod] = useState('GET');
    const [headers, setHeaders] = useState({});
    const [body, setBody] = useState('');
    const [response, setResponse] = useState(null);

    const handleSendRequest = async () => {
      try {
        const result = await fetch(endpoint, {
          method,
          headers: {
            Authorization: `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
            ...headers,
          },
          body: method !== 'GET' ? body : undefined,
        });

        setResponse(await result.json());
      } catch (error) {
        setResponse({ error: error.message });
      }
    };

    return (
      <div className="space-y-4">
        <div className="flex gap-2">
          <Select value={method} onValueChange={setMethod}>
            <SelectItem value="GET">GET</SelectItem>
            <SelectItem value="POST">POST</SelectItem>
            <SelectItem value="PATCH">PATCH</SelectItem>
            <SelectItem value="DELETE">DELETE</SelectItem>
          </Select>

          <Input
            value={endpoint}
            onChange={(e) => setEndpoint(e.target.value)}
            placeholder="/api/v1/conversations"
            className="flex-1"
          />

          <Button onClick={handleSendRequest}>Send</Button>
        </div>

        <Tabs defaultValue="headers">
          <TabsList>
            <TabsTrigger value="headers">Headers</TabsTrigger>
            <TabsTrigger value="body">Body</TabsTrigger>
          </TabsList>

          <TabsContent value="headers">
            <JSONEditor value={headers} onChange={setHeaders} />
          </TabsContent>

          <TabsContent value="body">
            <CodeEditor language="json" value={body} onChange={setBody} />
          </TabsContent>
        </Tabs>

        {response && (
          <div className="mt-4">
            <h3 className="mb-2 text-sm font-medium">Response</h3>
            <CodeBlock language="json">{JSON.stringify(response, null, 2)}</CodeBlock>
          </div>
        )}
      </div>
    );
  }
  ```

### 4.4 Webhook Management Interface

**Location:** `apps/web/app/developer/webhooks/`

- [ ] Webhook configuration interface:

  ```tsx
  // apps/web/app/developer/webhooks/page.tsx
  export default function WebhooksPage() {
    const { data: webhooks } = useWebhooks();

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Webhooks</h1>
          <CreateWebhookButton />
        </div>

        <WebhooksList webhooks={webhooks} />
        <WebhookDeliveryLogs />
      </div>
    );
  }
  ```

- [ ] Webhook creation form:

  ```tsx
  // components/developer/CreateWebhookForm.tsx
  export function CreateWebhookForm() {
    return (
      <form onSubmit={handleSubmit} className="space-y-6">
        <Input label="Endpoint URL" placeholder="https://your-app.com/webhooks" required />

        <div>
          <label className="text-sm font-medium">Events</label>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {availableEvents.map((event) => (
              <label key={event} className="flex items-center space-x-2">
                <Checkbox
                  checked={selectedEvents.includes(event)}
                  onChange={(checked) => handleEventToggle(event, checked)}
                />
                <span className="text-sm">{event}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="text-sm font-medium">Secret</label>
          <div className="mt-1 flex gap-2">
            <Input
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="webhook_secret_123"
            />
            <Button type="button" variant="outline" onClick={generateSecret}>
              Generate
            </Button>
          </div>
        </div>

        <Button type="submit">Create Webhook</Button>
      </form>
    );
  }
  ```

- [ ] Webhook testing interface:
  ```tsx
  // components/developer/WebhookTester.tsx
  export function WebhookTester({ webhook }: { webhook: Webhook }) {
    const [testEvent, setTestEvent] = useState('conversation.created');
    const [testPayload, setTestPayload] = useState('');

    const handleSendTest = async () => {
      const response = await fetch(`/api/v1/webhooks/${webhook.id}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event: testEvent,
          payload: JSON.parse(testPayload),
        }),
      });

      // Show result
    };

    return (
      <div className="space-y-4">
        <Select value={testEvent} onValueChange={setTestEvent}>
          {webhook.events.map((event) => (
            <SelectItem key={event} value={event}>
              {event}
            </SelectItem>
          ))}
        </Select>

        <CodeEditor
          language="json"
          value={testPayload}
          onChange={setTestPayload}
          placeholder="Test payload (optional)"
        />

        <Button onClick={handleSendTest}>Send Test Event</Button>
      </div>
    );
  }
  ```

### 4.5 Usage Analytics Dashboard

**Location:** `apps/web/app/developer/analytics/`

- [ ] Analytics overview:

  ```tsx
  // apps/web/app/developer/analytics/page.tsx
  export default function AnalyticsPage() {
    const { data: analytics } = useAnalytics();

    return (
      <div className="space-y-6">
        <AnalyticsOverview metrics={analytics.overview} />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <APIUsageChart data={analytics.apiUsage} />
          <WebhookDeliveryChart data={analytics.webhookDelivery} />
          <TopEndpointsTable data={analytics.topEndpoints} />
          <ErrorRatesChart data={analytics.errorRates} />
        </div>

        <CustomToolsAnalytics data={analytics.customTools} />
      </div>
    );
  }
  ```

- [ ] Real-time usage metrics:
  ```tsx
  // components/developer/APIUsageChart.tsx
  export function APIUsageChart({ data }: { data: UsageData[] }) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>API Usage</CardTitle>
          <CardDescription>Requests over time</CardDescription>
        </CardHeader>

        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="requests" stroke="#8884d8" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    );
  }
  ```

### 4.6 SDK Downloads & Documentation

**Location:** `apps/web/app/developer/sdks/`

- [ ] SDK download page:
  ```tsx
  // apps/web/app/developer/sdks/page.tsx
  export default function SDKsPage() {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold">SDKs & Libraries</h1>
          <p className="mt-2 text-gray-600">
            Official SDKs and community libraries for integrating with Reva
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          <SDKCard
            name="JavaScript SDK"
            description="For web applications and Node.js"
            language="javascript"
            downloadUrl="/sdks/reva-js-sdk.zip"
            docsUrl="/developer/docs/sdks/javascript"
          />

          <SDKCard
            name="Python SDK"
            description="For Python applications and scripts"
            language="python"
            downloadUrl="/sdks/reva-python-sdk.zip"
            docsUrl="/developer/docs/sdks/python"
          />

          <SDKCard
            name="React Widget"
            description="Drop-in React component"
            language="react"
            downloadUrl="/sdks/reva-react-widget.zip"
            docsUrl="/developer/docs/sdks/react"
          />
        </div>

        <QuickStartExamples />
      </div>
    );
  }
  ```

### 4.7 Sandbox Environment

**Location:** `apps/web/app/developer/sandbox/`

- [ ] Sandbox testing environment:

  ```tsx
  // apps/web/app/developer/sandbox/page.tsx
  export default function SandboxPage() {
    return (
      <div className="flex h-full flex-col">
        <div className="border-b p-4">
          <h1 className="text-xl font-semibold">API Sandbox</h1>
          <p className="text-sm text-gray-600">Test your integrations with sample data</p>
        </div>

        <div className="grid flex-1 grid-cols-1 lg:grid-cols-2">
          <SandboxRequestPanel />
          <SandboxResponsePanel />
        </div>
      </div>
    );
  }
  ```

- [ ] Sample data generator:
  ```tsx
  // components/developer/SampleDataGenerator.tsx
  export function SampleDataGenerator() {
    const generateSampleConversation = () => {
      return {
        id: 'conv_sandbox_123',
        customer_email: 'test@example.com',
        messages: [
          {
            role: 'user',
            content: 'I need help with my order',
            timestamp: new Date().toISOString(),
          },
        ],
      };
    };

    return (
      <div className="space-y-4">
        <h3 className="font-medium">Sample Data</h3>

        <div className="grid grid-cols-2 gap-2">
          <Button variant="outline" onClick={() => insertSampleData('conversation')}>
            Sample Conversation
          </Button>

          <Button variant="outline" onClick={() => insertSampleData('customer')}>
            Sample Customer
          </Button>
        </div>
      </div>
    );
  }
  ```

---

## Files to Create/Modify

| File                                        | Action | Purpose                       |
| ------------------------------------------- | ------ | ----------------------------- |
| `apps/web/app/developer/layout.tsx`         | Create | Developer portal layout       |
| `apps/web/app/developer/page.tsx`           | Create | Dashboard overview            |
| `apps/web/app/developer/api-keys/page.tsx`  | Create | API key management            |
| `apps/web/app/developer/webhooks/page.tsx`  | Create | Webhook management            |
| `apps/web/app/developer/tools/page.tsx`     | Create | Custom tools interface        |
| `apps/web/app/developer/analytics/page.tsx` | Create | Usage analytics               |
| `apps/web/app/developer/docs/page.tsx`      | Create | API documentation             |
| `apps/web/app/developer/sdks/page.tsx`      | Create | SDK downloads                 |
| `apps/web/app/developer/sandbox/page.tsx`   | Create | Testing environment           |
| `apps/web/components/developer/`            | Create | Developer portal components   |
| `apps/web/lib/hooks/useDeveloperAPI.ts`     | Create | Developer API hooks           |
| `apps/api/app/api/v1/developer/`            | Create | Developer portal backend APIs |

---

## Dependencies

```json
// Add to apps/web/package.json
{
  "dependencies": {
    "@monaco-editor/react": "^4.6.0",
    "recharts": "^2.8.0",
    "react-syntax-highlighter": "^15.5.0"
  }
}
```

---

## Testing

- [ ] Component tests for all developer portal interfaces
- [ ] Integration tests for API key creation and management
- [ ] E2E tests for complete developer onboarding flow
- [ ] Accessibility tests for developer portal
- [ ] Performance tests for analytics dashboard loading
- [ ] Security tests for API key display and storage

**Example Tests:**

```tsx
// __tests__/developer/APIKeysPage.test.tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import APIKeysPage from '@/app/developer/api-keys/page';

describe('API Keys Page', () => {
  it('should display existing API keys', async () => {
    render(<APIKeysPage />);

    await waitFor(() => {
      expect(screen.getByText('My Integration Key')).toBeInTheDocument();
    });
  });

  it('should create new API key', async () => {
    render(<APIKeysPage />);

    fireEvent.click(screen.getByText('Create API Key'));

    // Fill form
    fireEvent.change(screen.getByLabelText('Key Name'), {
      target: { value: 'Test Key' },
    });

    fireEvent.click(screen.getByText('Create'));

    await waitFor(() => {
      expect(screen.getByText('reva_test_sk_')).toBeInTheDocument();
    });
  });
});

// __tests__/developer/APIPlayground.test.tsx
describe('API Playground', () => {
  it('should send API request and display response', async () => {
    render(<APIPlayground />);

    // Set endpoint
    fireEvent.change(screen.getByPlaceholderText('/api/v1/conversations'), {
      target: { value: '/api/v1/conversations' },
    });

    // Send request
    fireEvent.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(screen.getByText('Response')).toBeInTheDocument();
    });
  });
});
```

---

## Acceptance Criteria

1. **Developer Onboarding:** New developers can create account and API key in under 15 minutes
2. **API Documentation:** Interactive docs with working examples for all endpoints
3. **Key Management:** Can create, view, rotate, and delete API keys with proper scopes
4. **Webhook Management:** Can configure webhooks and view delivery logs
5. **Usage Analytics:** Real-time metrics for API usage, errors, and performance
6. **SDK Downloads:** Working SDKs available for JavaScript, Python, and React
7. **Sandbox Testing:** Can test API calls with sample data without affecting production
8. **Security:** API keys are properly masked and stored securely

---

## Notes

- Focus on developer experience and ease of use
- Provide comprehensive examples and tutorials
- Implement proper error handling and user feedback
- Consider adding code generation tools for common use cases
- Add community features (forums, examples) in future iterations
- Ensure mobile-responsive design for developer portal
