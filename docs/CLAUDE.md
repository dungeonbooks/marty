# Marty - AI Bookstore Chatbot

## Project Overview
Python 3.13+ FastAPI application for AI bookstore chatbot. Uses Claude AI, PostgreSQL, Hardcover API. Discord interface.

## Dependency Management
**CRITICAL: Always use `uv` (NEVER pip):**
- `uv add <package>` - Add production dependency
- `uv add --group dev <package>` - Add dev dependency
- `uv sync` - Install dependencies
- `uv sync --group dev` - Install with dev dependencies
- `uv run <command>` - Run commands in venv

## Command Runner
**CRITICAL: Use `just` commands (NEVER raw pytest/ruff/ty directly):**
- `just --list` - Show all available commands
- `just dev` - Start development server with hot reload
- `just test` - Run tests (NOT `pytest`)
- `just test-file <filename>` - Run specific test file
- `just lint` - Lint code (NOT `ruff check`)
- `just format` - Format code (NOT `ruff format`)
- `just check` - Type check (NOT `ty check`)
- `just check-all` - Format, lint, and type check
- `just ci` - Fast checks (lint + type + unit tests)
- `just test-all` - Full test suite with infrastructure

## Code Quality Standards
- **Type hints required** on all functions
- **Modern Python**: Use `str | None` not `Optional[str]`
- **Async/await**: Required for I/O operations
- **Specific exceptions**: Not generic `Exception`
- **pathlib.Path**: NOT `os.path`
- **Structured logging**: Use logger with context

## Testing
- pytest with asyncio support
- Mock external APIs (avoid costs)
- `@pytest.mark.asyncio` for async tests
- 80%+ coverage requirement

## Database
- `just db-migrate` - Apply migrations
- `just db-revision "message"` - Create new migration
- `just db-reset` - Reset database
- PostgreSQL with async SQLAlchemy

## Key Files
- `src/main.py` - FastAPI application entry point
- `src/ai_client.py` - Claude AI integration
- `src/discord_bot/bot.py` - Discord bot implementation
- `justfile` - Command definitions (use these!)
- `pyproject.toml` - Dependencies and config
- `.cursor/rules/` - Project-specific guidelines

## Environment Variables
Required in `.env`:
- `DATABASE_URL` - PostgreSQL connection
- `ANTHROPIC_API_KEY` - Claude API key
- `HARDCOVER_API_TOKEN` - Book data API
- `DISCORD_BOT_TOKEN` - Discord bot token
