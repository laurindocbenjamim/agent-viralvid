## Rules for Antigravity Project

### 🏛️ Architectural Pattern & Project Structure
* **Modular Monolith (Bounded Contexts)**: Always design the application as a monolith, but strictly segregated by business domains (Bounded Contexts) [1]. Each domain must encapsulate its own logic, routing, and models to allow future microservices extraction if needed.
* **Backend Structure (FastAPI)**: Organize by domain features, not by technical layers. Avoid global `routers/` or `models/` folders.
  ```text
  src/
  ├── config/             # Global configurations & env variables
  ├── shared/             # Shared utilities, database session, middleware
  └── domains/            # Bounded Contexts
      ├── users/          # Users Domain
      │   ├── router.py   # Endpoints for this domain
      │   ├── service.py  # Business logic
      │   ├── models.py   # Database models
      │   └── schemas.py  # Pydantic input/output validation
      └── orders/         # Orders Domain
          ├── router.py
          └── service.py
  ```
* **Frontend Structure**: Organize by feature modules containing their own components, state, and API hooks.
  ```text
  src/
  ├── assets/             # Global styles, images, fonts
  ├── shared/             # Global UI components (Button, Input), global context/hooks
  └── modules/            # Bounded Contexts / Features
      ├── auth/           # Authentication Feature
      │   ├── components/ # Module-specific components
      │   ├── hooks/      # Module-specific state/queries (e.g., TanStack Query)
      │   └── AuthPage.tsx
      └── dashboard/      # Dashboard Feature
          ├── components/
          └── DashboardPage.tsx
  ```

### 🛡️ Development & Methodology
* **Always use TDD approach**: Write your tests before writing the actual production code to guarantee correctness from the start.
* **Always create regression tests**: Ensure new changes never break existing behavior.
    * **Frontend**: Implement tests using **Cypress** or **Playwright**.
    * **Backend**: Implement tests using **Pytest** (for Python components).

* **Always create stress tests**: Ensure high-load resilience by implementing
    * **Backend**: Validate endpoints using simulated peak traffic. Target maximum concurrent users. Monitor CPU, memory, and database connection pools. Identify bottlenecks, leaks, and failure points before deployment

### 🔍 Observability & Error Tracking
* **Mandatory Sentry Integration**: Always integrate Sentry into the application architecture from day one.
    * **Frontend**: Track client-side exceptions, user context, and UI performance issues.
    * **Backend**: Capture unhandled API exceptions (e.g., FastAPI), request context, and database performance bottlenecks.

### ⚡ Optimization & Code Quality
* **Always create optimized scripts**: Focus on performance, efficient memory usage, algorithms with low time complexity, and clean execution.
* **Strict file size limit**: Never create a file with more than **200 lines of code**. Split logic into smaller, reusable modules if it exceeds this limit.
* **Dry & Modular Code**: Avoid code duplication. Reuse components and functions to keep the codebase small and highly maintainable.

### 🪙 Token Optimization (AI-Driven Development)
* **Concise Code Generation**: Write compact, clean code without verbose comments. Use self-explanatory variable and function names to reduce code volume.
* **No Boilerplate**: Avoid generating placeholder code, repetitive setups, or unnecessary boilerplate files unless explicitly requested.
* **Incremental Updates**: When modifying code, only output the specific lines or functions that changed. Do not rewrite unchanged parts of the file.

### 🔒 Application Security (SecOps)
* **Zero Hardcoded Secrets**: Never hardcode API keys, DSNs, tokens, or passwords. Always use environment variables (`.env`) managed via `pydantic-settings` or `python-dotenv`.
* **Input Validation & Sanitization**: Always validate and sanitize user inputs on the backend (e.g., using Pydantic models in FastAPI) to prevent SQL Injection and XSS attacks.
* **Secure Dependencies**: Only use verified, up-to-date libraries. Run security audits on dependencies regularly.


## Documentation
Always add docstring documentation to functions and important line os codes

Always Create and update the README or other documentation file for each new feature added

# AI Agent & FastAPI Development Guidelines

## 1. Architectural Patterns (Use with Intent)
- NEVER implement design patterns blindly. Apply them only to solve real architectural complexity.
- FACADE: Use to simplify FastAPI route handlers. Routes should only call a Facade/Service layer, keeping the HTTP layer thin.
- STRATEGY: Implement to abstract LLM providers (OpenAI, Anthropic, Ollama) and tools, making them interchangeable.
- STATE: Use to manage autonomous agent lifecycles (e.g., Planning, Executing, Reviewing, Idle).
- OBSERVER: Implement for event-driven logging, token counting, or streaming internal agent thoughts to WebSockets.
- DECORATOR: Apply for cross-cutting concerns like LLM response caching, rate limiting, and automated retries.

## 2. Financial & Currency Precision (Critical)
- NEVER use primitive `float` or `double` for currency, prices, or monetary values.
- ALWAYS use Python's built-in `decimal.Decimal` for monetary arithmetic to prevent floating-point rounding errors.
- Prefer encapsulating money into a Value Object (Data Class or Pydantic Model) containing both amount and currency.
- Example Pattern:
```python
from decimal import Decimal
from pydantic import BaseModel, Field

class Money(BaseModel):
    amount: Decimal = Field(..., max_digits=10, decimal_places=2)
    currency: str = "USD"
```

## 3. Strict Type Safety & Primitives
- Avoid "Primitive Obsession". If a primitive type (str, int) carries specific business rules or validation, wrap it in a Pydantic Custom Type or Value Object.
- ALWAYS use explicit Python type hints (`str`, `int`, `bool`, `dict`, `list`, or `typing` generics).
- Enable strict mode validation in Pydantic models when handling untrusted LLM outputs or external API payloads.
- Use `NewType` or Pydantic custom annotations for structural IDs (e.g., `AgentID`, `SessionID`) instead of generic strings.

## 4. FastAPI & Async Best Practices
- Define asynchronous endpoints (`async def`) for I/O bound operations, especially when waiting for LLM responses.
- Implement structured error handling using Custom FastAPI HTTPExceptions.
- Keep agent state externalized (e.g., in Redis or PostgreSQL) to ensure FastAPI instances remain stateless and horizontally scalable.


## 5. SOLID Principles Integration
- SRP: Keep FastAPI routers thin. Move orchestration to Facades and domain rules to Value Objects.
- OCP: Use the Strategy pattern to add new LLM providers or Agent Tools without modifying existing orchestrator code.
- LSP: Ensure all subclasses of an Agent State or LLM Strategy strictly adhere to the base class method signatures and return types.
- ISP: Create small, focused interfaces for Agent Tools (e.g., separate reading tools from mutating tools).
- DIP: Never instantiate LLM clients or repositories directly inside the Agent logic. Inject abstractions using FastAPI's `Depends`.
