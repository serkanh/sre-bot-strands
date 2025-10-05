# SRE Bot Strands

A FastAPI-based application powered by AWS Strands framework for building AI agents with Bedrock integration.

## Features

- **Multi-Agent Architecture**: Intelligent query routing with specialized agents
  - **Coordinator Agent**: Routes queries to appropriate specialist agents
  - **FinOps Agent**: AWS cost analysis using Cost Explorer MCP tools
  - **Kubernetes Agent**: K8s cluster management for both K3s and EKS
  - Extensible design for adding more specialist agents
- **Two-Service Architecture**: Separate API and Web services sharing the same codebase
  - **API Service** (Port 8000): Strict API endpoints without CORS or static files
  - **Web Service** (Port 8001): Full-featured web UI with CORS and static file serving
- **AWS Bedrock Integration**: Claude 4.0 Sonnet model via AWS Bedrock
- **MCP Integration**: Model Context Protocol support for AWS Cost Explorer
- **Real-time Bot Activity**: Toggleable status display showing agent thinking and tool usage
- **Session Management**: File-based conversation history storage
- **Docker Support**: Complete docker-compose setup for easy deployment
- **Type Safety**: Full Pydantic validation and type hints
- **Code Quality**: Configured with Ruff for linting and formatting

## Multi-Agent Architecture

The application uses a **coordinator-specialist pattern** where a coordinator agent routes queries to specialized agents:

### Coordinator Agent
- Routes user queries to appropriate specialist agents
- Handles general SRE questions directly
- Maintains conversation context across interactions

### FinOps Agent
- Specialized in AWS cost analysis and optimization
- Integrates with AWS Cost Explorer via MCP (Model Context Protocol)
- Provides:
  - Cost breakdowns by service, region, or time period
  - Cost comparisons between periods
  - Cost forecasting
  - Optimization recommendations

### Kubernetes Agent
- Specialized in Kubernetes cluster management and troubleshooting
- Works with both K3s (local) and EKS (production) clusters
- Provides:
  - Pod listing and status checking
  - Pod logs retrieval
  - Deployment information
  - Namespace management
  - Event monitoring
  - Cluster troubleshooting

#### Local K3s Setup

The project includes a K3s cluster running via Docker Compose for local development:

**Architecture**: containerd-in-Docker (not Docker-in-Docker)
- K3s runs in a privileged Docker container
- Uses containerd as the container runtime (standard for Kubernetes)
- Pods run inside containerd within the K3s container
- Same architecture as tools like kind (Kubernetes IN Docker)

**Access the cluster**:
```bash
# From host machine
kubectl --kubeconfig=./k3s_data/kubeconfig/kubeconfig.yaml \
  --server=https://127.0.0.1:6443 --insecure-skip-tls-verify get pods -A

# From inside K3s container
docker exec -it sre-bot-k3s kubectl get pods -A

# Exec into a pod
docker exec -it sre-bot-k3s kubectl exec -it -n kube-system <pod-name> -- sh
```

**Note**: The K3s cluster is configured with `seccomp=unconfined` for macOS compatibility.

### Example Queries

**Cost/FinOps Queries** (routed to FinOps Agent):
- "What are my AWS costs for last month?"
- "Show me EC2 spending trends"
- "Forecast next month's AWS costs"
- "Compare costs between Q1 and Q2"

**Kubernetes Queries** (routed to Kubernetes Agent):
- "What pods are running in my cluster?"
- "Show me logs from pod xyz-123"
- "List all deployments in namespace production"
- "What events occurred in the default namespace?"
- "Check the status of pod frontend-abc"

**General SRE Queries** (handled by Coordinator):
- "How do I troubleshoot EC2 instances?"
- "What's the best practice for Docker deployments?"

**Note**: AWS Cost Explorer API charges $0.01 per request. Use wisely!

## Architecture

The application uses a single codebase with `SERVICE_MODE` environment variable to determine which service to run:

```
┌──────────────────────────────────────────────────┐
│              Docker Compose                      │
└──────────────────────────────────────────────────┘
    │                │                    │
    │          ┌─────▼─────┐        ┌────▼──────┐
    │          │ API Service│        │Web Service│
    │          │ Port: 8000 │        │Port: 8001 │
    │          │ MODE: api  │        │MODE: web  │
    │          │ - No CORS  │        │- CORS     │
    │          │ - API only │        │- Static   │
    │          └─────┬──────┘        │- Chat UI  │
    │                │               └─────┬─────┘
    │                │                     │
    │                └─────────┬───────────┘
    │                          │
    │                ┌─────────▼──────────┐
    │                │  Shared Codebase   │
    │                │  - Agents          │
    │                │  - Services        │
    │                │  - API Routes      │
    │                │  - Models          │
    │                └────────────────────┘
    │
┌───▼────────────────────────────────────┐
│ K3s Server (Local K8s Cluster)         │
│ ┌────────────────────────────────────┐ │
│ │ containerd (Container Runtime)     │ │
│ │  ┌──────────┐  ┌──────────┐       │ │
│ │  │ coredns  │  │ traefik  │  ...  │ │
│ │  │   pod    │  │   pod    │       │ │
│ │  └──────────┘  └──────────┘       │ │
│ └────────────────────────────────────┘ │
└────────────────────────────────────────┘
```

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- AWS Account with Bedrock access
- AWS credentials configured with permissions:
  - Cost Explorer: `ce:GetCostAndUsage`, `ce:GetCostForecast`, `ce:GetDimensionValues`
  - Bedrock: `bedrock:InvokeModel`, `bedrock:ListFoundationModels`
- Kubernetes cluster (optional, for K8s queries):
  - K3s (local development) or EKS (production)
  - Valid kubeconfig file
- `uvx` (for running MCP servers) - installed with `pip install uv`

## Quick Start

### 1. Environment Setup

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your AWS credentials. You have two options:

**Option 1: Use AWS Profile (Recommended)**
```env
# Service Configuration
SERVICE_MODE=api  # or "web"
PORT=8000

# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=your_profile_name

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# Application Configuration
SESSION_STORAGE_PATH=./sessions
LOG_LEVEL=INFO

# Kubernetes Configuration (optional)
KUBECONFIG=./k3s_data/kubeconfig/kubeconfig.yaml
```

**Option 2: Use AWS Access Keys**
```env
# Service Configuration
SERVICE_MODE=api  # or "web"
PORT=8000

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# Application Configuration
SESSION_STORAGE_PATH=./sessions
LOG_LEVEL=INFO

# Kubernetes Configuration (optional)
KUBECONFIG=./k3s_data/kubeconfig/kubeconfig.yaml
```

### 2. Local Development

#### Using UV (Recommended)

```bash
# Install dependencies
uv sync

# Run API service
SERVICE_MODE=api uv run uvicorn app.main:app --reload --port 8000

# Run Web service (in another terminal)
SERVICE_MODE=web uv run uvicorn app.main:app --reload --port 8001
```

#### Using Docker Compose

```bash
# Start both services
docker compose up

# Or build and start
docker compose up --build

# Run in background
docker compose up -d
```

### 3. Access the Application

- **API Service**: http://localhost:8000
  - API Docs: http://localhost:8000/docs
  - Health Check: http://localhost:8000/health

- **Web Service**: http://localhost:8001
  - Chat UI: http://localhost:8001/
  - API Docs: http://localhost:8001/docs
  - Health Check: http://localhost:8001/health

## API Endpoints

### Health Check
```http
GET /health
```

Returns service status and Bedrock connectivity.

### Chat
```http
POST /api/chat
Content-Type: application/json

{
  "user_id": "user123",
  "message": "Hello, how can you help me?"
}
```

Returns chat response with event stream data.

### Configuration
```http
GET /api/config
```

Get current agent configuration.

```http
POST /api/config
Content-Type: application/json

{
  "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

Update agent configuration dynamically.

### Session Management
```http
GET /api/session/{user_id}
```

Get conversation history for a user.

```http
DELETE /api/session/{user_id}
```

Clear conversation history for a user.

## Project Structure

```
sre-bot-strands/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Application factory
│   ├── config.py               # Settings management
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── coordinator_agent.py # Coordinator agent
│   │   ├── finops_agent.py      # FinOps specialist
│   │   └── kubernetes_agent.py  # Kubernetes specialist
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py           # Health check endpoint
│   │   └── routes.py           # API routes
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   └── session_manager.py  # Session management
│   └── static/
│       ├── index.html          # Chat UI
│       ├── app.js              # Frontend logic
│       └── styles.css          # Styling
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_web.py
│   ├── test_coordinator.py
│   ├── test_finops_agent.py
│   └── test_kubernetes_agent.py
├── sessions/                   # Session storage (gitignored)
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── ruff.toml
└── README.md
```

## Development

### Code Quality

```bash
# Run linter
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check . --fix

# Format code
uv run ruff format .
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app

# Run specific test file
uv run pytest tests/test_api.py
```

### Type Checking

```bash
# Run mypy
uv run mypy app/
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_MODE` | `api` | Service mode: `api` or `web` |
| `PORT` | `8000` | Service port |
| `AWS_REGION` | `us-east-1` | AWS region |
| `AWS_PROFILE` | - | (Optional) AWS profile name from `~/.aws/credentials` |
| `AWS_ACCESS_KEY_ID` | - | (Optional) AWS access key (not needed if using profile) |
| `AWS_SECRET_ACCESS_KEY` | - | (Optional) AWS secret key (not needed if using profile) |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Bedrock model ID |
| `SESSION_STORAGE_PATH` | `./sessions` | Session storage directory |
| `LOG_LEVEL` | `INFO` | Logging level |
| `KUBECONFIG` | - | (Optional) Path to kubeconfig file for K8s access |

### Service Modes

#### API Mode (`SERVICE_MODE=api`)
- Pure REST API endpoints
- No CORS middleware
- No static file serving
- Designed for programmatic access

#### Web Mode (`SERVICE_MODE=web`)
- All API endpoints
- CORS enabled for browser access
- Static file serving for UI
- Chat interface with real-time status

### AWS Authentication

The application supports two methods for AWS authentication:

#### Method 1: AWS Profile (Recommended for Docker)

Using AWS profiles allows you to manage multiple AWS accounts and avoid hardcoding credentials:

1. Ensure you have AWS CLI configured with profiles in `~/.aws/credentials`:
   ```ini
   [your_profile_name]
   aws_access_key_id = YOUR_ACCESS_KEY
   aws_secret_access_key = YOUR_SECRET_KEY
   ```

2. Set the profile in your `.env` file:
   ```env
   AWS_PROFILE=your_profile_name
   ```

3. Docker Compose automatically mounts `~/.aws` folder (read-only) to the containers

#### Method 2: Access Keys

Directly specify AWS credentials (useful for CI/CD or environments without AWS CLI):

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

**Note**: If `AWS_PROFILE` is set, it takes precedence over access keys.

## Real-time Bot Activity

The web interface includes a toggleable status panel that shows:

- **Thinking**: When the agent is processing your request
- **Tool Usage**: When the agent is using external tools
- **Responding**: When the agent is generating the response

Toggle this feature using the "Show Bot Activity" checkbox in the header.

## Docker Deployment

### Build and Run

```bash
# Build images
docker compose build

# Start services
docker compose up

# Stop services
docker compose down

# View logs
docker compose logs -f

# Start only specific services (e.g., without K3s for production)
docker compose up api web
```

**Note**: The docker-compose setup includes a local K3s cluster for development. In production environments connecting to external Kubernetes clusters (like EKS), you can exclude the K3s service.

### Production Considerations

1. **Environment Variables**: Use Docker secrets or external secret management
2. **AWS Authentication**:
   - For production, use IAM roles or AWS profiles instead of hardcoded keys
   - The `~/.aws` folder is mounted as read-only to containers
   - Ensure your AWS profile has permissions for `bedrock:InvokeModel` and `bedrock:ListFoundationModels`
3. **CORS**: Configure `allow_origins` in `app/main.py` for production domains
4. **Health Checks**: Docker health checks are configured for both services
5. **Volumes**: Session data is persisted via volume mounts
6. **Networking**: Services communicate via Docker bridge network

## Troubleshooting

### Bedrock Connection Issues

1. Verify AWS credentials are correct
2. Ensure IAM user has `bedrock:InvokeModel` permission
3. Check if the model is available in your region
4. Review health check endpoint: `/health`

### Session Storage Issues

1. Check `SESSION_STORAGE_PATH` directory exists and is writable
2. Verify sufficient disk space
3. Review logs for permission errors

### Docker Issues

1. Ensure ports 8000 and 8001 are not in use
2. Check Docker daemon is running
3. Verify `.env` file is present
4. Review container logs: `docker compose logs`

### K3s Cluster Issues

1. **Check cluster status**:
   ```bash
   docker compose logs k3s-server --tail 50
   kubectl --kubeconfig=./k3s_data/kubeconfig/kubeconfig.yaml \
     --server=https://127.0.0.1:6443 --insecure-skip-tls-verify get nodes
   ```

2. **Pods not starting**: Verify K3s is configured with `seccomp=unconfined` for macOS compatibility

3. **Connection errors**: Ensure kubeconfig server address matches:
   - From host: Use `https://127.0.0.1:6443`
   - From containers: Use `https://sre-bot-k3s:6443`

4. **Reset cluster**:
   ```bash
   docker compose down k3s-server
   docker volume rm sre-bot-strands_k3s-server
   rm -rf ./k3s_data/kubeconfig/*
   docker compose up -d k3s-server
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

[Specify your license here]

## Support

For issues and questions:
- Create an issue in the repository
- Contact the development team

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [AWS Strands](https://github.com/awslabs/strands)
- Uses [Claude 4.0 Sonnet](https://www.anthropic.com/claude) via AWS Bedrock
