# SRE Bot Strands

A FastAPI-based application powered by AWS Strands framework for building AI agents with Bedrock integration.

## Features

- **Two-Service Architecture**: Separate API and Web services sharing the same codebase
  - **API Service** (Port 8000): Strict API endpoints without CORS or static files
  - **Web Service** (Port 8001): Full-featured web UI with CORS and static file serving
- **AWS Bedrock Integration**: Claude 4.0 Sonnet model via AWS Bedrock
- **Real-time Bot Activity**: Toggleable status display showing agent thinking and tool usage
- **Session Management**: File-based conversation history storage
- **Docker Support**: Complete docker-compose setup for easy deployment
- **Type Safety**: Full Pydantic validation and type hints
- **Code Quality**: Configured with Ruff for linting and formatting

## Architecture

The application uses a single codebase with `SERVICE_MODE` environment variable to determine which service to run:

```
┌─────────────────────────────────────────┐
│          Docker Compose                 │
└─────────────────────────────────────────┘
         │                    │
   ┌─────▼─────┐        ┌────▼──────┐
   │ API Service│        │Web Service│
   │ Port: 8000 │        │Port: 8001 │
   │ MODE: api  │        │MODE: web  │
   │ - No CORS  │        │- CORS     │
   │ - API only │        │- Static   │
   └─────┬──────┘        │- Chat UI  │
         │               └─────┬─────┘
         │                     │
         └─────────┬───────────┘
                   │
         ┌─────────▼──────────┐
         │  Shared Codebase   │
         │  - Agents          │
         │  - Services        │
         │  - API Routes      │
         │  - Models          │
         └────────────────────┘
```

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- AWS Account with Bedrock access
- AWS credentials configured

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
│   │   └── strands_agent.py    # Strands agent wrapper
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
│   └── test_agent.py
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
```

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
