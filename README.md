# Marty - Dungeon Books SMS & Discord Chatbot

[![Railway Deployment](https://img.shields.io/badge/Railway-Deployed-brightgreen)](https://railway.com/project/9ae0f484-5538-4866-9757-a6931049b1e9?environmentId=dddc87ce-de5b-4928-8e27-3c40c088ef05)

A chatbot that recommends books and chats with customers via SMS and Discord.

Marty is a burnt-out wizard who used to do software engineering and now works at Dungeon Books. He's genuinely magical but completely casual about it.

## What It Does

- Chat with customers about books via SMS and Discord
- Give personalized book recommendations
- Remember conversation history
- Integrate with Hardcover API for book data
- Handle customer info and orders (eventually)
- Send responses that sound like a real person texting

**Mention `@marty` to chat in a thread**

![](docs/chat.jpg)

**Rich embeds via `/book`, `!book`, or chatting about a book**

![](docs/embed.jpg)

**Recent releases via `/recent`**

![](docs/recent.jpg)

## Tech Stack

- Python 3.13
- FastAPI with async support
- Hypercorn ASGI server (dual-stack IPv4/IPv6)
- Claude for conversations
- PostgreSQL with SQLAlchemy
- Hardcover API for book data
- pytest for testing
- Ruff for code quality
- ty for type checking
- uv for dependency management
- just for command running

## Requirements

- Python 3.13
- uv (for dependency management)
- just (for command running)
- PostgreSQL database (Supabase recommended)
- Redis server (for rate limiting and caching)
- Anthropic API key
- Hardcover API token
- Sinch SMS API credentials

## Setup

### Install Dependencies

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install just command runner
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/bin

# Install GNU parallel (required for CI and fast local checks)
# Debian/Ubuntu:
sudo apt-get update && sudo apt-get install -y parallel
# macOS (with Homebrew):
brew install parallel

# Clone repository
git clone <repository-url>
cd marty

# Complete project setup
just setup
```

### Environment Setup

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

Required environment variables:

```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
ANTHROPIC_API_KEY=your_claude_api_key_here
HARDCOVER_API_TOKEN=Bearer your_hardcover_token_here
SINCH_API_TOKEN=your_sinch_api_token
SINCH_SERVICE_PLAN_ID=your_service_plan_id
SINCH_FROM_NUMBER=your_virtual_phone_number
SINCH_WEBHOOK_SECRET=your_webhook_secret
REDIS_URL=redis://localhost:6379/0
```

### Database Setup

Production (Supabase):

```bash
# Apply migrations
alembic upgrade head
```

Local development (SQLite):

```bash
# Set SQLite in .env
DATABASE_URL=sqlite+aiosqlite:///./marty.db

# Apply migrations
alembic upgrade head
```

### Verify Setup

```bash
# Test database connection
python src/database.py

# Comprehensive integration test (⚠️ makes real API calls - costs money)
uv run python scripts/smoke_test.py
```

### Run Application

Development server with hot reload:

```bash
uv run fastapi dev src/main.py
```

Production server:

```bash
uv run python src/main.py
```

Server runs on http://localhost:8000 with dual-stack IPv4/IPv6 binding.

## API Endpoints

### Health Check

```
GET /health
```

Returns database connectivity and system status.

### SMS Webhook

```
POST /webhook/sms
```

Request:

```json
{
  "From": "+1234567890",
  "Text": "looking for a good fantasy book",
  "MessageUUID": "unique-id"
}
```

Response:

```json
{
  "status": "received",
  "message_id": "uuid"
}
```

### Chat Interface (for testing)

```
POST /chat
```

Request:

```json
{
  "message": "looking for a good fantasy book",
  "phone": "+1234567890"
}
```

Response:

```json
{
  "response": "try the name of the wind by rothfuss, really solid fantasy. good worldbuilding and the magic system is interesting",
  "conversation_id": "uuid",
  "customer_id": "uuid"
}
```

## Development

### Development Scripts

**Interactive Testing** (internal use only):

```bash
just chat
```

Terminal chat interface for testing responses without the SMS pipeline.

**SMS Testing** (⚠️ uses real API):

```bash
just sms
```

Interactive SMS testing interface for sending real SMS messages and testing webhook processing. Requires Sinch API credentials.

**Integration Testing** (⚠️ costs money):

```bash
# Enable real API calls and run smoke test
MARTY_ENABLE_REAL_API_TESTS=1 just smoke-test
```

Comprehensive test of all integrations: Claude, Hardcover API, and database.
Makes real API calls - use sparingly.

### Test Suite

**Unit Tests** (fast, no infrastructure):

```bash
# Run unit tests only
just ci

# Or manually
pytest -m "not integration"
```

**Integration Tests** (requires infrastructure):

```bash
# Run all tests including integration
just test-all

# Run only integration tests
just test-integration
```

**Additional Test Commands**:

```bash
# Specific test files
just test-file test_ai_client.py

# With coverage
just test-cov

# Verbose output
just test-verbose
```

**Testing**: All Claude API calls are automatically mocked in tests to prevent costs. Real API calls only happen in smoke tests when `MARTY_ENABLE_REAL_API_TESTS=1` is set.

### Code Quality

**Pre-commit Hooks** (recommended):

```bash
# Install hooks (runs linting, type checking, and unit tests)
just pre-commit-install

# Run all pre-commit checks manually
just pre-commit-run
```

**Manual Code Quality**:

```bash
# Format code
just format

# Lint code
just lint

# Type check
just check

# Run all checks
just check-all
```

### Database Migrations

```bash
# Generate migration
just db-revision "description"

# Apply migrations
just db-migrate

# Rollback
just db-rollback

# Reset database
just db-reset
```

## CI/CD Infrastructure

**Available Commands**:

```bash
# Show all available commands
just --list

# Fast CI checks (no infrastructure)
just ci

# Full CI with integration tests
just ci-full

# Watch mode for development
just watch
```

**Parallelized Checks:**

- Lint, type check, and security scan (Bandit) are run in parallel for faster feedback using GNU parallel.
- GNU parallel is required for CI and pre-commit hooks. On Linux, it is auto-installed by pre-commit/CI. On macOS, install it manually with `brew install parallel`.
- If you see errors like `parallel: command not found`, install GNU parallel as above.

**Test Infrastructure**:

- Docker Compose setup for isolated testing
- PostgreSQL and Redis containers for integration tests
- Automatic infrastructure management with `just test-all`
- CI-ready with proper test isolation

## Configuration

### Claude

Get API key from console.anthropic.com.
Add to .env as `ANTHROPIC_API_KEY`.

### Hardcover API

Request access at hardcover.app/api.
Add token as `HARDCOVER_API_TOKEN=Bearer your_token`.

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `ANTHROPIC_API_KEY`: Anthropic API key
- `HARDCOVER_API_TOKEN`: Book data API token
- `BOOKSHOP_AFFILIATE_ID`: Optional affiliate links
- `SINCH_API_TOKEN`: Sinch API token for SMS sending
- `SINCH_SERVICE_PLAN_ID`: Sinch service plan identifier
- `SINCH_FROM_NUMBER`: Virtual phone number for sending SMS
- `SINCH_WEBHOOK_SECRET`: Webhook signature verification
- `REDIS_URL`: Redis connection string for rate limiting
- `SMS_RATE_LIMIT`: Messages per window (default: 5)
- `SMS_RATE_LIMIT_WINDOW`: Rate limit window in seconds (default: 60)
- `SMS_RATE_LIMIT_BURST`: Burst limit per hour (default: 10)
- `DEFAULT_PHONE_REGION`: Default region for phone parsing (default: US)
- `DEBUG`: true/false
- `LOG_LEVEL`: INFO/DEBUG

## Architecture

### Conversation Layer

Claude handles conversation and book recommendations.

### Database Layer

PostgreSQL with async SQLAlchemy for data persistence.
Alembic for schema migrations.

### API Layer

FastAPI with async endpoints.
Hypercorn ASGI server for production deployment.

### Personality System

Marty's personality is defined in `prompts/marty_system_prompt.md` and `prompts/marty_discord_system_prompt.md`.
Casual texting style with wizard references.

## Database Schema

- **Customers**: Phone numbers and basic info
- **Conversations**: Message threads with context
- **Messages**: Individual texts with direction tracking
- **Books**: Catalog from Hardcover API
- **Inventory**: Stock levels and availability
- **Orders**: Purchases and fulfillment

## Current Implementation Status

Implemented:

- FastAPI application with async support
- Conversation engine with history and book lookup
- Database layer with migrations
- Hardcover API integration
- Comprehensive test suite
- Terminal chat interface
- SMS webhook handler with signature verification
- SMS provider integration with multi-message support
- Redis-based rate limiting with burst protection
- Phone number validation and normalization
- Discord bot integration with thread management

In development:

- Square API for payments
- Purchase flow
- Inventory management

## Troubleshooting

### Database Issues

```bash
# Test connection
just test-db

# Check environment
echo $DATABASE_URL

# Reset database
just db-reset
```

### Claude Issues

```bash
# Test integration (⚠️ costs money)
MARTY_ENABLE_REAL_API_TESTS=1 just smoke-test

# Check API key
echo $ANTHROPIC_API_KEY
```

### GNU parallel Not Found

If you see errors about `parallel: command not found` during CI or local runs, install GNU parallel:

- **Debian/Ubuntu:** `sudo apt-get update && sudo apt-get install -y parallel`
- **macOS (Homebrew):** `brew install parallel`

### Test Failures

```bash
# Run unit tests only (fast)
just ci

# Verbose output
just test-verbose

# Specific test with output
just test-file test_database.py

# Check if integration tests need infrastructure
just test-integration
```

### CI/CD Issues

```bash
# Check pre-commit setup
just pre-commit-run

# Verify all quality checks pass
just check-all

# Full CI pipeline
just ci-full
```

### Debug Mode

```bash
# Add to .env
DEBUG=true
LOG_LEVEL=DEBUG
```

## Contributing

1. Fork repository
2. Create feature branch
3. Make changes
4. Run quality checks: `just check-all`
5. Run tests: `just ci`
6. Commit (pre-commit hooks run automatically)
7. Submit pull request

**Development Workflow**:

- Use `just ci` for fast feedback during development
- Use `just test-all` for comprehensive testing before commits
- Pre-commit hooks enforce code quality automatically

## Monitoring

### Railway Built-in Monitoring

- **Health Check**: `/health` endpoint monitors database connectivity and migration status
- **Logs**: Railway provides real-time logs in dashboard
- **Metrics**: Built-in Railway metrics for CPU, memory, and request volume
- **Deployment**: [Railway Project Dashboard](https://railway.com/project/9ae0f484-5538-4866-9757-a6931049b1e9?environmentId=dddc87ce-de5b-4928-8e27-3c40c088ef05)

## License

MIT License - see [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Script Wizards
