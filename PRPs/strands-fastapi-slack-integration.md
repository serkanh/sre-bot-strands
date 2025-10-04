# PRP: AWS Strands FastAPI with Two-Service Architecture

## Executive Summary

Build a unified codebase that deploys as **two separate FastAPI services** serving the AWS Strands framework:

1. **API Service** (Port 8000): RESTful API service (prepared for future Slack Bot integration)
2. **Web Service** (Port 8001): Minimal playground UI for testing and experimentation

**Key Architecture Decision**: Both services share the same codebase but are differentiated by a `SERVICE_MODE` environment variable at startup. This provides clean separation of concerns, independent scaling, and enhanced security while maintaining a single, maintainable codebase.

**Initial Scope**: Focus on infrastructure setup with two-service architecture and functional Web UI. API service will have basic health/chat endpoints, ready for future Slack integration.

The application is fully dockerized with docker-compose for seamless local development, using AWS Bedrock for model inference.

## Feature Requirements

From INITIAL.md:

- FastAPI-based API serving AWS Strands framework
- Dockerized with docker-compose for easy local development
- **Single codebase deployed as two separate services (API + Web)**
- API service with RESTful endpoints (Slack integration is future work, out of initial scope)
- Web service with minimal, simple interface (inspired by Strands playground)
- AWS Bedrock inference for models
- Utilize AWS Documentation MCP Server and context7 capabilities

**Initial Build Scope**:

- ✅ Two-service docker-compose setup (API + Web)
- ✅ Shared codebase with SERVICE_MODE differentiation
- ✅ Functional Web UI with chat interface
- ✅ AWS Bedrock integration for Strands agents
- ✅ Session management across both services
- ⏸️ Slack Bot integration (future work, API service prepared)

## Architecture Overview

### System Design

```
┌────────────────────────────────────────────────────────────┐
│                    Docker Compose                           │
│                                                              │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │   API Service :8000     │  │   Web Service :8001     │  │
│  │  (SERVICE_MODE=api)     │  │  (SERVICE_MODE=web)     │  │
│  │                         │  │                         │  │
│  │  ┌──────────────────┐   │  │  ┌──────────────────┐   │  │
│  │  │ API Endpoints    │   │  │  │ Web UI Endpoints │   │  │
│  │  │ /api/chat        │   │  │  │ /api/chat        │   │  │
│  │  │ /api/config      │   │  │  │ /api/config      │   │  │
│  │  │ /health          │   │  │  │ /health          │   │  │
│  │  │                  │   │  │  │ + Static Files   │   │  │
│  │  │ (Future: Slack)  │   │  │  │ + CORS           │   │  │
│  │  └────────┬─────────┘   │  │  └────────┬─────────┘   │  │
│  └───────────┼─────────────┘  └───────────┼─────────────┘  │
│              │                            │                │
│              └──────────┬─────────────────┘                │
│                         │                                  │
│              ┌──────────▼──────────┐                       │
│              │   Shared Resources  │                       │
│              │                     │                       │
│              │ • Strands Agent     │                       │
│              │ • Session Manager   │                       │
│              │ • Configuration     │                       │
│              └──────────┬──────────┘                       │
│                         │                                  │
│              ┌──────────▼──────────┐                       │
│              │  Shared Volume      │                       │
│              │  ./sessions/        │                       │
│              └─────────────────────┘                       │
└────────────────────────┬───────────────────────────────────┘
                         │
                ┌────────▼────────┐
                │  AWS Bedrock    │
                │ (Claude Model)  │
                └─────────────────┘
```

### Service Separation Benefits

1. **Clean Separation**: API service has no web/CORS overhead, Web service optimized for browser access
2. **Independent Scaling**: Can run multiple API containers without scaling web service
3. **Security**: Each service only exposes necessary routes
4. **Development**: Can work on one service without affecting the other
5. **Production-Ready**: Standard microservices pattern with shared business logic
6. **Future-Ready**: API service prepared for future integrations (Slack, webhooks, etc.)

### Project Structure

```
/
├── app/
│   ├── __init__.py
│   ├── main.py                    # App factory with conditional routing
│   ├── config.py                  # Settings with SERVICE_MODE
│   ├── agents/
│   │   ├── __init__.py
│   │   └── strands_agent.py       # Shared Strands Agent wrapper
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py              # Chat/config endpoints (shared)
│   │   └── health.py              # Health check (both services)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   └── session_manager.py     # Shared session persistence
│   └── static/                    # Web interface (Web service only)
│       ├── index.html
│       ├── app.js
│       └── styles.css
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_web.py
│   └── test_agent.py
├── sessions/                       # Shared session storage (gitignored)
├── pyproject.toml                  # uv package manager config
├── uv.lock                         # Dependency lockfile
├── Dockerfile                      # Single Dockerfile for both services
├── docker-compose.yml              # Two service definitions
├── .dockerignore
├── .env.example
├── .gitignore
├── README.md
└── ruff.toml                       # Linting config
```

## Technical Context

### Core Technologies

#### 1. AWS Strands Agents

- **Documentation**: <https://strandsagents.com/latest/documentation/docs/user-guide/quickstart/>
- **SDK Repository**: <https://github.com/strands-agents/sdk-python>
- **Installation**: `pip install strands-agents strands-agents-tools`
- **Key Concepts**:
  - Model-driven AI agent development
  - Built-in and custom tools via `@tool` decorator
  - Async streaming via `stream_async()` method
  - Multiple model provider support (Bedrock, Anthropic, OpenAI, Ollama)
  - Observability through traces, metrics, logs

**Basic Agent Pattern**:

```python
from strands import Agent, tool

@tool
def my_tool(param: str) -> str:
    """Tool description for the agent."""
    return f"Result: {param}"

agent = Agent(
    tools=[my_tool],
    model="bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0"
)
result = agent("User prompt here")
```

**Async Streaming Pattern** (Critical for FastAPI and Web UI):

```python
async for event in agent.stream_async(prompt):
    if event.type == "agent_message":
        # Agent's text response - display in chat
        pass
    elif event.type == "tool_use":
        # Agent is using a tool - show "Using tool: {tool_name}"
        tool_name = event.data.get("tool_name")
        pass
    elif event.type == "thinking":
        # Agent is thinking - show "Thinking..."
        pass
    # Return these events to frontend for real-time status updates
```

**Event Types for Web UI Status Display**:
- `thinking`: Show "🤔 Thinking..." status
- `tool_use`: Show "🔧 Using tool: {tool_name}" status
- `agent_message`: Display the actual response
- Can be toggled on/off in Web UI settings

#### 2. FastAPI

- **Documentation**: <https://fastapi.tiangolo.com/deployment/docker/>
- **Best Practices**: <https://betterstack.com/community/guides/scaling-python/fastapi-docker-best-practices/>
- **Key Features**:
  - Async/await native support
  - Automatic OpenAPI documentation
  - Pydantic integration for validation
  - Static file serving via `StaticFiles`
  - CORS middleware for web UI

**App Factory Pattern** (Critical for this architecture):

```python
from fastapi import FastAPI
from app.config import Settings

def create_app() -> FastAPI:
    settings = Settings()

    if settings.SERVICE_MODE == "api":
        # API Service: Slack endpoints only
        app = FastAPI(title="Strands API Service")
        app.include_router(slack_router, prefix="/slack")
        app.include_router(health_router)
    else:  # web
        # Web Service: UI endpoints + static files
        app = FastAPI(title="Strands Web UI")
        app.add_middleware(CORSMiddleware, allow_origins=["*"])
        app.mount("/static", StaticFiles(directory="app/static"), name="static")
        app.include_router(web_router, prefix="/api")
        app.include_router(health_router)

    return app

app = create_app()
```

**Docker Best Practices**:

- Multi-stage builds for smaller images
- Copy dependencies before code for better caching
- Use `.dockerignore` to exclude unnecessary files
- Volume mounts for live reload in development
- Health checks in docker-compose

#### 3. AWS Bedrock

- **Documentation**: <https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started-api-ex-python.html>
- **Boto3 Reference**: <https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock.html>
- **Integration**: Strands uses Bedrock natively via `BedrockModel` class
- **Authentication**: AWS credentials via environment variables or AWS CLI config
- **Region**: Must enable model access in AWS Bedrock console

**Strands Bedrock Configuration**:

```python
from strands.models import BedrockModel

model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name=os.environ.get("AWS_REGION", "us-east-1")
)

agent = Agent(model=model, tools=[...])
```

#### 4. UV Package Manager

- **Documentation**: <https://docs.astral.sh/uv/guides/projects/>
- **Features**:
  - 10-100x faster than pip/poetry
  - Automatic virtual environment management
  - Lockfile for reproducible builds (uv.lock)
  - Python version management via `.python-version`
  - Seamless pyproject.toml integration

**Key Commands**:

```bash
uv init                        # Initialize project
uv add fastapi uvicorn        # Add dependencies
uv sync                       # Install from lockfile
uv run python app/main.py     # Run with environment
uv run pytest                 # Run tests
```

### Reference Implementation

**Strands Playground Example** (Primary Reference):

- **Repository**: <https://github.com/strands-agents/samples/tree/main/04-UX-demos/05-strands-playground>
- **Key Files**:
  - `app/main.py`: FastAPI setup, agent initialization, endpoints
  - `app/requirements.txt`: Dependencies (fastapi 0.115.12, uvicorn 0.34.2, pydantic 2.11.4)
  - `static/`: Web interface files

**Key Patterns from Strands Playground**:

1. **Custom Agent Class**: Extend `Agent` with custom initialization
2. **Session Management**: Save/restore conversation state per user
3. **Dynamic Configuration**: Endpoints to update model settings, system prompt, tools
4. **Metrics Tracking**: Return latency, token usage with responses
5. **Error Handling**: Comprehensive logging and graceful fallbacks

## Implementation Blueprint

### Configuration Strategy

**app/config.py with SERVICE_MODE**:

```python
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    # Service Configuration
    SERVICE_MODE: Literal["api", "web"] = "api"
    PORT: int = 8000

    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Bedrock Configuration
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # Application Configuration
    SESSION_STORAGE_PATH: str = "./sessions"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
```

### Main Application Factory

**app/main.py with conditional routing**:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import Settings
from app.api import routes, health

def create_app() -> FastAPI:
    """Create FastAPI app based on SERVICE_MODE environment variable."""
    settings = Settings()

    if settings.SERVICE_MODE == "api":
        # API Service: RESTful API only, no CORS, no static files
        app = FastAPI(
            title="Strands API Service",
            description="RESTful API for AWS Strands agents",
            version="1.0.0"
        )

        # Include API routes (no static files, no CORS)
        app.include_router(routes.router, prefix="/api", tags=["api"])
        app.include_router(health.router, tags=["health"])

    else:  # web mode
        # Web Service: UI endpoints, static files, CORS enabled
        app = FastAPI(
            title="Strands Web UI",
            description="Web playground for AWS Strands agents",
            version="1.0.0"
        )

        # Enable CORS for browser access
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Serve static files
        app.mount("/static", StaticFiles(directory="app/static"), name="static")

        # Include web routes (same endpoints as API, but with CORS and static files)
        app.include_router(routes.router, prefix="/api", tags=["web"])
        app.include_router(health.router, tags=["health"])

    return app

app = create_app()
```

### Docker Compose Configuration

**docker-compose.yml with two services**:

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: strands-api
    environment:
      - SERVICE_MODE=api
      - PORT=8000
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID}
      - SESSION_STORAGE_PATH=/app/sessions
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app/app          # Live reload for development
      - ./sessions:/app/sessions # Shared session storage
    command: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  web:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: strands-web
    environment:
      - SERVICE_MODE=web
      - PORT=8001
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID}
      - SESSION_STORAGE_PATH=/app/sessions
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    ports:
      - "8001:8001"
    volumes:
      - ./app:/app/app          # Live reload for development
      - ./sessions:/app/sessions # Shared session storage
    command: uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Dockerfile (Single, Shared)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY app/ ./app/

# Create sessions directory
RUN mkdir -p sessions

# Expose ports (both services use same image)
EXPOSE 8000 8001

# Default command (overridden by docker-compose)
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Critical Gotchas & Considerations

### Shared Resources

1. **Session Storage**: Both services access `./sessions` volume - file-based storage works due to shared filesystem
2. **AWS Credentials**: Both services need AWS access - share same credentials
3. **Environment Variables**: API service needs Slack tokens, Web service doesn't - docker-compose handles this
4. **Port Configuration**: Must use different ports (8000 vs 8001) to avoid conflicts

### Service-Specific Considerations

**API Service**:

1. No CORS middleware (not needed, Slack webhooks only)
2. No static file serving
3. Only Slack and health endpoints exposed
4. Requires `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET`
5. Must respond to Slack within 3 seconds (use `ack()`)

**Web Service**:

1. CORS enabled for browser access
2. Static files mounted at `/static`
3. Web UI and health endpoints exposed
4. No Slack tokens required
5. Can take longer to respond (no 3-second limit)

### AWS Bedrock

1. **Model Access**: Must enable model access in AWS Bedrock console for your region
2. **IAM Permissions**: Required permissions: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
3. **Region Availability**: Claude models not available in all regions - use `us-east-1` or `us-west-2`
4. **Costs**: Bedrock charges per token - monitor usage
5. **Rate Limits**: Requests per minute limits apply

### Slack Integration

1. **App Configuration**: Must create Slack app, enable Event Subscriptions, set Request URL to `http://your-domain:8000/slack/events`
2. **Token Verification**: Slack verifies requests with signing secret - don't skip this
3. **3-Second Rule**: Must acknowledge Slack events within 3 seconds (use `ack()`)
4. **User IDs**: Slack user IDs (e.g., U12345) differ from web session IDs
5. **Scopes**: Required OAuth scopes: `app_mentions:read`, `chat:write`, `im:history`, `im:read`

### Strands Agents

1. **Async Streaming**: Use `stream_async()` for non-blocking responses
2. **Tool Initialization**: Tools must be initialized before agent creation
3. **Model IDs**: Bedrock model IDs have specific format: `anthropic.claude-3-5-sonnet-20241022-v2:0`
4. **Context Management**: Strands manages conversation history - don't duplicate
5. **Error Handling**: Agent errors should be caught and logged, don't crash the app

### Docker & Development

1. **Volume Mounts**: Required for live code reload - mount `./app` to `/app/app`
2. **Shared Sessions**: Both services mount same `./sessions` directory
3. **AWS Credentials**: Pass via environment or mount `~/.aws` (not recommended for production)
4. **Port Conflicts**: Ensure 8000 and 8001 are available on host
5. **Hot Reload**: Uvicorn `--reload` flag enables auto-restart on code changes

### Session Management

1. **Concurrency**: File-based storage may have race conditions - acceptable for MVP
2. **Cleanup**: Sessions directory will grow - implement cleanup strategy
3. **Serialization**: Ensure agent state is JSON-serializable
4. **User Isolation**: Separate sessions by user_id to avoid crosstalk
5. **Cross-Service**: Sessions are shared between API and Web services via volume mount

## Dependencies (pyproject.toml)

```toml
[project]
name = "sre-bot-strands"
version = "0.1.0"
description = "AWS Strands FastAPI with Slack Integration"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "strands-agents>=1.0.0",
    "strands-agents-tools>=1.0.0",
    "pydantic>=2.11.0",
    "pydantic-settings>=2.0.0",
    "boto3>=1.35.0",
    "python-dotenv>=1.0.0",
]

# Note: slack-bolt can be added later when implementing Slack integration

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "httpx>=0.27.0",  # for FastAPI TestClient
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.11"
strict = true
```

## Implementation Tasks (Ordered)

### Phase 1: Project Initialization

1. **Initialize Project**
   - [ ] Run `uv init` to create project structure
   - [ ] Create `pyproject.toml` with dependencies
   - [ ] Run `uv sync` to create lockfile and install dependencies
   - [ ] Create directory structure (app/, tests/, sessions/)
   - [ ] Create `.python-version` file with `3.11`

### Phase 2: Configuration Setup

2. **Configuration Management**
   - [ ] Create `app/config.py` with Pydantic Settings class
   - [ ] Add `SERVICE_MODE: Literal["api", "web"]` field
   - [ ] Add `PORT` field with default 8000
   - [ ] Add all AWS, Slack, and application settings
   - [ ] Create `.env.example` with all required environment variables
   - [ ] Add `.gitignore` for .env, sessions/, .venv/, etc.

### Phase 3: Shared Components

3. **Strands Agent Implementation**
   - [ ] Create `app/agents/strands_agent.py`
   - [ ] Implement `StrandsAgent` class extending `Agent`
   - [ ] Configure Bedrock model with environment variables
   - [ ] Add built-in tools from strands-agents-tools
   - [ ] Implement `async_chat()` method using `stream_async()`

4. **Session Management**
   - [ ] Create `app/services/session_manager.py`
   - [ ] Implement `SessionManager` class with file-based storage
   - [ ] Add methods: `load_session()`, `save_session()`, `create_session()`
   - [ ] Ensure sessions/ directory is created automatically
   - [ ] Handle concurrent access gracefully

5. **Pydantic Models**
   - [ ] Create `app/models/schemas.py`
   - [ ] Define request/response models: `ChatRequest`, `ChatResponse`, `ConfigUpdate`
   - [ ] Add validation rules

### Phase 4: API Endpoints

6. **Health Check Endpoint (Shared)**
   - [ ] Create `app/api/health.py`
   - [ ] Implement `/health` GET endpoint
   - [ ] Test AWS Bedrock connectivity
   - [ ] Return status with service checks and SERVICE_MODE

7. **Shared API Endpoints**
   - [ ] Create `app/api/routes.py`
   - [ ] Implement `POST /api/chat` endpoint with support for streaming events (thinking, tool_use, agent_message)
   - [ ] Return event stream data in response for real-time status updates
   - [ ] Implement `GET /api/config` endpoint
   - [ ] Implement `POST /api/config` endpoint
   - [ ] Implement `GET /api/session/{user_id}` endpoint
   - [ ] Add proper error handling and logging
   - [ ] Note: These endpoints are shared by both services

### Phase 5: Main Application

8. **FastAPI Application Factory**
   - [ ] Create `app/main.py` with `create_app()` factory function
   - [ ] Load settings from `Settings()`
   - [ ] Implement conditional routing based on `SERVICE_MODE`
   - [ ] For API mode: include routes router at /api, health router (no CORS, no static files)
   - [ ] For Web mode: add CORS middleware, mount static files, include routes router at /api, health router
   - [ ] Add global exception handler
   - [ ] Configure logging based on LOG_LEVEL

### Phase 6: Web Interface

9. **Web Interface (Web Service Only)**
    - [ ] Create `app/static/index.html` with chat UI
    - [ ] Create `app/static/app.js` with API calls and rendering logic
    - [ ] Create `app/static/styles.css` with responsive design
    - [ ] Implement message display, input handling
    - [ ] **Display real-time bot activity status (toggleable)**: Show "Thinking...", "Using tool: X", "Processing..." during agent operations with UI toggle to enable/disable
    - [ ] Add configuration panel for model settings
    - [ ] Display metrics (tokens, latency)
    - [ ] Keep design minimal and functional

### Phase 7: Dockerization

10. **Docker Configuration**
    - [ ] Create `Dockerfile` with Python 3.11-slim base
    - [ ] Install uv package manager
    - [ ] Copy pyproject.toml and uv.lock first (caching)
    - [ ] Run `uv sync --frozen`
    - [ ] Copy application code
    - [ ] Create sessions/ directory
    - [ ] Expose ports 8000 and 8001
    - [ ] Create `.dockerignore` to exclude .git, .venv, sessions, __pycache__

11. **Docker Compose Setup**
    - [ ] Create `docker-compose.yml` with two services: `api` and `web`
    - [ ] Configure `api` service with `SERVICE_MODE=api`, port 8000
    - [ ] Configure `web` service with `SERVICE_MODE=web`, port 8001
    - [ ] Add volume mounts: `./app:/app/app`, `./sessions:/app/sessions`
    - [ ] Configure environment variables from .env
    - [ ] Add health checks for both services
    - [ ] Set uvicorn command with --reload for development
    - [ ] Test build: `docker-compose build`

### Phase 8: Testing

12. **Testing Setup**
    - [ ] Create `tests/test_api.py` with API endpoint tests
    - [ ] Create `tests/test_web.py` with Web service tests
    - [ ] Create `tests/test_agent.py` with agent tests
    - [ ] Add `conftest.py` with fixtures for both service modes
    - [ ] Configure pytest.ini or pyproject.toml with test settings

### Phase 9: Code Quality

13. **Code Quality Tools**
    - [ ] Add `ruff.toml` configuration
    - [ ] Run `uv run ruff format .`
    - [ ] Run `uv run ruff check --fix .`
    - [ ] Configure mypy, run `uv run mypy app/`
    - [ ] Fix all type errors and lint warnings

### Phase 10: Documentation

14. **Documentation**
    - [ ] Create comprehensive `README.md`
    - [ ] Document the two-service architecture
    - [ ] Document prerequisites (Docker, AWS credentials)
    - [ ] Add quick start instructions (how to run both services)
    - [ ] Document environment variables for both services
    - [ ] Add troubleshooting section
    - [ ] Include example .env values
    - [ ] Document how to test each service independently
    - [ ] Note that Slack integration is future work

### Phase 11: Final Validation

15. **Final Validation**
    - [ ] Run all validation gates (see below)
    - [ ] Test API service endpoints (chat, config, health)
    - [ ] Test Web service functionality (UI, endpoints)
    - [ ] Verify both services can access shared sessions
    - [ ] Verify AWS Bedrock connectivity from both services
    - [ ] Test service separation (API shouldn't serve static files, Web should)
    - [ ] Test independent scaling (multiple API containers)

## Validation Gates (Executable)

Run these commands to validate the implementation:

```bash
# 1. Code Formatting & Linting
uv run ruff format .
uv run ruff check --fix .

# 2. Type Checking
uv run mypy app/

# 3. Unit Tests
uv run pytest tests/ -v

# 4. Docker Build
docker-compose build

# 5. Start Both Services
docker-compose up -d

# 6. Wait for services to be ready
sleep 10

# 7. Health Check - API Service
curl -f http://localhost:8000/health || echo "API health check failed"

# 8. Health Check - Web Service
curl -f http://localhost:8001/health || echo "Web health check failed"

# 9. Web UI Accessibility
curl -f http://localhost:8001/static/index.html || echo "Web UI not accessible"

# 10. Web API Chat Endpoint Test
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "message": "Hello"}' || echo "Web chat API failed"

# 11. Verify services are separate (API should NOT serve static files)
curl -f http://localhost:8000/static/index.html && echo "API serving static files (WRONG!)" || echo "API correctly NOT serving static files (CORRECT)"

# 12. Test API service chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "api_test_user", "message": "Hello from API service"}' || echo "API chat endpoint failed"

# 13. Check logs for both services
docker-compose logs api | tail -20
docker-compose logs web | tail -20

# 14. Stop Services
docker-compose down
```

## Success Criteria

- [ ] All validation gates pass without errors
- [ ] Docker-compose brings up both services successfully
- [ ] API service (port 8000) responds to health checks
- [ ] Web service (port 8001) responds to health checks and serves UI
- [ ] API service does NOT serve static files
- [ ] API service chat endpoint works correctly
- [ ] Both services can access shared sessions directory
- [ ] Chat functionality works in web interface
- [ ] Configuration panel works in web interface
- [ ] Session management persists conversation history across both services
- [ ] Logs show correct SERVICE_MODE for each service
- [ ] README provides clear setup instructions for both services

## Additional Resources

### Documentation

- Strands Quickstart: <https://strandsagents.com/latest/documentation/docs/user-guide/quickstart/>
- Strands SDK: <https://github.com/strands-agents/sdk-python>
- Strands Playground: <https://github.com/strands-agents/samples/tree/main/04-UX-demos/05-strands-playground>
- FastAPI Docker: <https://fastapi.tiangolo.com/deployment/docker/>
- AWS Bedrock Python: <https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started-api-ex-python.html>
- UV Package Manager: <https://docs.astral.sh/uv/guides/projects/>

### Example Code

- AWS Sample Course: <https://github.com/aws-samples/sample-getting-started-with-strands-agents-course>
- Bedrock Code Examples: <https://docs.aws.amazon.com/code-library/latest/ug/python_3_bedrock-runtime_code_examples.html>

### Blog Posts

- Strands 1.0 Announcement: <https://aws.amazon.com/blogs/opensource/introducing-strands-agents-1-0-production-ready-multi-agent-orchestration-made-simple/>
- FastAPI Best Practices: <https://betterstack.com/community/guides/scaling-python/fastapi-docker-best-practices/>

---

## PRP Self-Assessment

### Quality Checklist

- [x] All necessary context included (Strands, FastAPI, Slack, Bedrock, Docker)
- [x] Validation gates are executable by AI agent
- [x] References existing patterns from Strands playground
- [x] Clear implementation path with ordered tasks
- [x] Error handling and gotchas documented comprehensively
- [x] Complete dependency list with versions
- [x] **Architecture diagram showing two-service separation**
- [x] **App factory pattern with SERVICE_MODE switching**
- [x] **Docker-compose configuration with two services**
- [x] Specific URLs to documentation
- [x] Code examples and patterns provided
- [x] Success criteria clearly defined

### Confidence Score: **9/10**

**Rationale**: This PRP provides comprehensive context with a **cleaner two-service architecture** including:

- Complete technical specifications with reference implementations
- **Two-service separation via SERVICE_MODE environment variable**
- **Single Dockerfile, single codebase, two deployments**
- **Shared resources (agents, sessions) with independent routing**
- All dependencies with versions and configuration
- Critical gotchas specific to each technology **and service separation**
- Executable validation gates **testing both services independently**
- Ordered implementation tasks (16 phases, granular steps)
- Real code patterns from Strands playground example
- Specific documentation URLs for all technologies

**Potential Challenges** (accounting for -1 point):

- First-time Slack app setup may require clarification on OAuth scopes
- AWS Bedrock model access enablement is manual, might need troubleshooting
- Web interface design is "minimal" - interpretation may vary

**Mitigation**: The PRP provides extensive references and examples to handle these edge cases. The AI agent can research further using provided URLs if needed. The two-service architecture is simpler and more production-ready than the original single-service approach.
