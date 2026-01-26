# Phase 3: Custom Tools SDK

> **Parent:** [M8 Developer Platform](../m8-developer-platform.md)  
> **Duration:** 1.5 weeks  
> **Status:** Not Started  
> **Dependencies:** Phase 1 (Public API), Phase 2 (Webhooks)

---

## Goal

Enable developers to extend AI capabilities with custom actions and tools that integrate seamlessly with the agent's decision-making process using dynamic tool loading and secure execution.

---

## Tasks

### 3.1 Tool Definition Format & Validation

**Location:** `apps/api/app/services/custom_tools.py`

- [ ] Define YAML-based tool specification format:

  ```yaml
  # Example: loyalty_points_tool.yaml
  name: check_loyalty_points
  description: "Check customer's loyalty points balance and tier status"
  version: '1.0.0'

  triggers:
    - 'loyalty points'
    - 'rewards balance'
    - 'how many points'
    - 'membership tier'

  parameters:
    - name: customer_email
      type: string
      required: true
      source: conversation # Auto-filled from context
      description: "Customer's email address"

    - name: include_history
      type: boolean
      required: false
      default: false
      description: 'Include points earning history'

  endpoint:
    url: 'https://{{store.loyalty_api_url}}/api/v1/customers/{{customer_email}}/points'
    method: GET
    headers:
      Authorization: 'Bearer {{store.loyalty_api_key}}'
      Content-Type: 'application/json'
    timeout: 10

  response_mapping:
    points_balance: 'data.current_balance'
    tier: 'data.membership_tier'
    points_to_next_tier: 'data.points_needed_for_next_tier'
    expiring_points: 'data.expiring_soon'

  response_template: |
    You have {{points_balance}} loyalty points and you're a {{tier}} member!
    {% if points_to_next_tier > 0 %}
    You need {{points_to_next_tier}} more points to reach the next tier.
    {% endif %}
    {% if expiring_points > 0 %}
    Note: {{expiring_points}} points will expire soon.
    {% endif %}

  error_handling:
    not_found: "I couldn't find your loyalty account. Please make sure you're signed up for our rewards program."
    api_error: "I'm having trouble accessing the loyalty system right now. Please try again later."
  ```

- [ ] Tool validation service:
  ```python
  class ToolValidator:
      def validate_definition(self, tool_yaml: str) -> ValidationResult:
          """Validate tool definition against schema."""

      def validate_security(self, tool_def: ToolDefinition) -> SecurityResult:
          """Check for security issues (URL validation, etc.)."""

      def validate_endpoint(self, tool_def: ToolDefinition) -> EndpointResult:
          """Test tool endpoint connectivity and response format."""
  ```

### 3.2 Tool Registry & Management

**Location:** `apps/api/app/models/custom_tools.py`

- [ ] Create `custom_tools` table:

  ```sql
  CREATE TABLE custom_tools (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    definition_yaml TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(organization_id, name)
  );

  CREATE TABLE tool_executions (
    id UUID PRIMARY KEY,
    tool_id UUID REFERENCES custom_tools(id),
    conversation_id UUID REFERENCES conversations(id),
    parameters_json JSONB,
    response_json JSONB,
    execution_time_ms INTEGER,
    status VARCHAR(20), -- success, error, timeout
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
  );
  ```

- [ ] Tool management API:

  ```python
  # apps/api/app/api/v1/public/tools.py

  @router.post("/tools")
  async def create_tool(
      tool: ToolCreate,
      auth: OAuth2Token = Depends(require_scope("tools:write"))
  ):
      """Upload and register a custom tool."""

  @router.get("/tools")
  async def list_tools(
      auth: OAuth2Token = Depends(require_scope("tools:read"))
  ):
      """List all custom tools for organization."""

  @router.put("/tools/{tool_id}")
  async def update_tool(
      tool_id: UUID,
      tool: ToolUpdate,
      auth: OAuth2Token = Depends(require_scope("tools:write"))
  ):
      """Update tool definition."""

  @router.post("/tools/{tool_id}/test")
  async def test_tool(
      tool_id: UUID,
      test_params: dict,
      auth: OAuth2Token = Depends(require_scope("tools:write"))
  ):
      """Test tool execution with sample parameters."""
  ```

### 3.3 Dynamic Tool Loading & LangGraph Integration

**Location:** `apps/api/app/services/tool_loader.py`

- [ ] Dynamic tool loading for LangGraph:

  ```python
  class CustomToolLoader:
      async def load_tools_for_store(self, store_id: UUID) -> List[Tool]:
          """Load all active custom tools for a store."""

      def create_langchain_tool(self, tool_def: ToolDefinition) -> Tool:
          """Convert tool definition to LangChain Tool object."""

      async def execute_tool(
          self,
          tool_name: str,
          parameters: dict,
          context: ConversationContext
      ) -> ToolResult:
          """Execute custom tool with given parameters."""
  ```

- [ ] LangGraph agent integration:

  ```python
  # apps/api/app/services/agent.py (modify existing)

  class RevaAgent:
      async def _load_tools(self, store_id: UUID) -> List[Tool]:
          """Load both built-in and custom tools."""
          tools = await self._load_builtin_tools()
          custom_tools = await self.tool_loader.load_tools_for_store(store_id)
          return tools + custom_tools

      async def _should_use_tool(self, tool_name: str, query: str) -> bool:
          """Determine if tool should be used based on triggers."""
          tool_def = await self.tool_registry.get_tool(tool_name)
          return any(trigger.lower() in query.lower() for trigger in tool_def.triggers)
  ```

### 3.4 Secure Tool Execution Environment

**Location:** `apps/api/app/services/tool_executor.py`

- [ ] Sandboxed execution with security controls:

  ```python
  class ToolExecutor:
      MAX_EXECUTION_TIME = 30  # seconds
      MAX_RESPONSE_SIZE = 1024 * 1024  # 1MB
      ALLOWED_DOMAINS = []  # Configurable per organization

      async def execute(
          self,
          tool_def: ToolDefinition,
          parameters: dict,
          context: ExecutionContext
      ) -> ExecutionResult:
          """Execute tool with security controls."""

      def _validate_url(self, url: str) -> bool:
          """Validate URL against security policies."""

      def _apply_rate_limits(self, tool_id: UUID) -> bool:
          """Check tool-specific rate limits."""

      async def _make_http_request(
          self,
          url: str,
          method: str,
          headers: dict,
          data: dict = None
      ) -> httpx.Response:
          """Make HTTP request with timeout and size limits."""
  ```

- [ ] Template rendering with Jinja2:
  ```python
  class TemplateRenderer:
      def render_url(self, url_template: str, context: dict) -> str:
          """Render URL template with store/customer context."""

      def render_headers(self, headers: dict, context: dict) -> dict:
          """Render header templates with secrets."""

      def render_response(self, template: str, response_data: dict) -> str:
          """Render response template for AI consumption."""
  ```

### 3.5 Tool Context & Parameter Resolution

**Location:** `apps/api/app/services/tool_context.py`

- [ ] Context resolution service:

  ```python
  class ToolContextResolver:
      async def resolve_parameters(
          self,
          tool_def: ToolDefinition,
          conversation: Conversation,
          explicit_params: dict = None
      ) -> dict:
          """Resolve tool parameters from conversation context."""

      async def get_customer_context(self, conversation: Conversation) -> dict:
          """Extract customer information from conversation."""

      async def get_store_context(self, store_id: UUID) -> dict:
          """Get store-specific configuration and secrets."""

      def extract_from_conversation(
          self,
          conversation: Conversation,
          parameter_name: str
      ) -> Any:
          """Extract parameter value from conversation history."""
  ```

- [ ] Parameter sources:
  ```python
  class ParameterSource(str, Enum):
      CONVERSATION = "conversation"  # Extract from chat history
      CUSTOMER = "customer"          # From customer profile
      STORE = "store"               # From store configuration
      EXPLICIT = "explicit"         # Provided by AI/user
      CONTEXT = "context"           # From page/product context
  ```

### 3.6 Tool Analytics & Monitoring

**Location:** `apps/api/app/services/tool_analytics.py`

- [ ] Tool usage tracking:

  ```python
  class ToolAnalytics:
      async def track_execution(
          self,
          tool_id: UUID,
          execution_time: int,
          success: bool,
          error: str = None
      ):
          """Track tool execution metrics."""

      async def get_tool_metrics(
          self,
          tool_id: UUID,
          period: str = "7d"
      ) -> ToolMetrics:
          """Get tool performance metrics."""

      async def detect_anomalies(self, tool_id: UUID) -> List[Anomaly]:
          """Detect unusual tool behavior (high error rates, etc.)."""
  ```

- [ ] Tool performance dashboard data:
  ```python
  @dataclass
  class ToolMetrics:
      total_executions: int
      success_rate: float
      avg_execution_time: float
      error_breakdown: Dict[str, int]
      usage_trend: List[Tuple[date, int]]
  ```

---

## Example Custom Tools

### 1. Loyalty Points Checker

```yaml
name: check_loyalty_points
description: "Check customer's loyalty points and tier status"
version: '1.0.0'

triggers:
  - 'loyalty points'
  - 'rewards balance'
  - 'how many points'

parameters:
  - name: customer_email
    type: string
    required: true
    source: conversation

endpoint:
  url: 'https://api.smile.io/v1/customers/{{customer_email}}/points'
  method: GET
  headers:
    Authorization: 'Bearer {{store.smile_api_key}}'

response_mapping:
  points: 'data.points_balance'
  tier: 'data.vip_tier'

response_template: |
  You have {{points}} loyalty points and you're a {{tier}} member!
```

### 2. Appointment Booking

```yaml
name: book_appointment
description: 'Book in-store appointment for customer'
version: '1.0.0'

triggers:
  - 'book appointment'
  - 'schedule visit'
  - 'make appointment'

parameters:
  - name: customer_email
    type: string
    required: true
    source: conversation
  - name: service_type
    type: string
    required: true
    source: explicit
  - name: preferred_date
    type: string
    required: false
    source: explicit

endpoint:
  url: 'https://{{store.booking_domain}}/api/appointments'
  method: POST
  headers:
    Authorization: 'Bearer {{store.booking_api_key}}'
  body:
    customer_email: '{{customer_email}}'
    service: '{{service_type}}'
    requested_date: '{{preferred_date}}'

response_mapping:
  appointment_id: 'data.id'
  scheduled_time: 'data.datetime'
  location: 'data.store_location'

response_template: |
  Great! I've booked your {{service_type}} appointment for {{scheduled_time}} at our {{location}} location.
  Your appointment ID is {{appointment_id}}.
```

### 3. Size Recommendation

```yaml
name: get_size_recommendation
description: 'Get AI-powered size recommendation for customer'
version: '1.0.0'

triggers:
  - 'what size'
  - 'size recommendation'
  - 'fit guide'

parameters:
  - name: product_id
    type: string
    required: true
    source: context
  - name: customer_measurements
    type: object
    required: false
    source: customer

endpoint:
  url: 'https://api.fitanalytics.com/size-advice'
  method: POST
  headers:
    Authorization: 'Bearer {{store.fitanalytics_key}}'
  body:
    product_id: '{{product_id}}'
    measurements: '{{customer_measurements}}'

response_mapping:
  recommended_size: 'recommendation.size'
  confidence: 'recommendation.confidence'
  fit_notes: 'recommendation.notes'

response_template: |
  Based on the product and your measurements, I recommend size {{recommended_size}}.
  {% if confidence > 0.8 %}This recommendation has high confidence.{% endif %}
  {{fit_notes}}
```

---

## Files to Create/Modify

| File                                | Action | Purpose                    |
| ----------------------------------- | ------ | -------------------------- |
| `app/models/custom_tools.py`        | Create | Tool data models           |
| `app/services/custom_tools.py`      | Create | Tool management service    |
| `app/services/tool_loader.py`       | Create | Dynamic tool loading       |
| `app/services/tool_executor.py`     | Create | Secure tool execution      |
| `app/services/tool_context.py`      | Create | Parameter resolution       |
| `app/services/tool_analytics.py`    | Create | Usage tracking and metrics |
| `app/api/v1/public/tools.py`        | Create | Tool management API        |
| `app/schemas/public/tools.py`       | Create | Tool Pydantic schemas      |
| `app/services/agent.py`             | Modify | Integrate custom tools     |
| `app/workers/tool_tasks.py`         | Create | Async tool execution tasks |
| `alembic/versions/xxx_add_tools.py` | Create | Database migration         |

---

## Dependencies

```toml
# Add to pyproject.toml
jinja2 = "^3.1"           # Template rendering
pyyaml = "^6.0"           # YAML parsing
jsonschema = "^4.17"      # Tool definition validation
httpx = "^0.27"           # HTTP client for tool execution
```

---

## Testing

- [ ] Unit tests for tool definition validation (valid/invalid YAML)
- [ ] Unit tests for template rendering with various contexts
- [ ] Integration tests for tool execution with mock endpoints
- [ ] Security tests for URL validation and parameter injection
- [ ] Performance tests for tool loading and execution speed
- [ ] End-to-end tests with LangGraph agent using custom tools

**Example Tests:**

```python
@pytest.mark.asyncio
async def test_tool_definition_validation():
    valid_yaml = """
    name: test_tool
    description: "Test tool"
    triggers: ["test"]
    parameters: []
    endpoint:
      url: "https://api.example.com/test"
      method: GET
    """

    validator = ToolValidator()
    result = validator.validate_definition(valid_yaml)
    assert result.is_valid is True

@pytest.mark.asyncio
async def test_tool_execution():
    tool_def = ToolDefinition(
        name="test_tool",
        endpoint={"url": "https://httpbin.org/json", "method": "GET"}
    )

    executor = ToolExecutor()
    result = await executor.execute(tool_def, {}, ExecutionContext())

    assert result.success is True
    assert result.response_data is not None

@pytest.mark.asyncio
async def test_parameter_resolution():
    conversation = await create_test_conversation()
    tool_def = ToolDefinition(
        parameters=[
            {"name": "customer_email", "source": "conversation", "required": True}
        ]
    )

    resolver = ToolContextResolver()
    params = await resolver.resolve_parameters(tool_def, conversation)

    assert "customer_email" in params
    assert params["customer_email"] == conversation.customer_email

@pytest.mark.asyncio
async def test_langraph_integration():
    # Test that custom tools are loaded into LangGraph agent
    agent = RevaAgent(store_id=test_store_id)
    tools = await agent._load_tools(test_store_id)

    # Should include both built-in and custom tools
    tool_names = [tool.name for tool in tools]
    assert "check_loyalty_points" in tool_names
    assert "get_order_status" in tool_names  # built-in tool
```

---

## Acceptance Criteria

1. **Tool Definition:** Can create tools using YAML format with validation
2. **Dynamic Loading:** Custom tools are loaded into AI agent at runtime
3. **Secure Execution:** Tools execute with proper security controls and timeouts
4. **Parameter Resolution:** Tool parameters are resolved from conversation context
5. **Template Rendering:** Response templates work with Jinja2 syntax
6. **Error Handling:** Graceful handling of tool failures and API errors
7. **Analytics:** Tool usage is tracked with performance metrics
8. **LangGraph Integration:** Tools work seamlessly with existing agent flow

---

## Notes

- Start with simple HTTP GET tools, add POST/PUT support iteratively
- Consider tool versioning for backward compatibility
- Implement tool marketplace in future phases
- Add tool testing sandbox environment
- Consider rate limiting per tool to prevent abuse
- Add tool approval workflow for enterprise customers
