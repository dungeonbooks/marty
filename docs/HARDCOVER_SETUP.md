# Hardcover API Setup Instructions

## Quick Start

1. **Set your API token**:
   ```bash
   export HARDCOVER_API_TOKEN="Bearer your_actual_token_here"
   ```

2. **Install dependencies** (if not already installed):
   ```bash
   uv sync
   ```

3. **Test the connection** using the exploration script:
   ```bash
   uv run python scripts/explore_hardcover_api.py
   ```

4. **Run the test suite**:
   ```bash
   uv run pytest tests/test_hardcover.py -v
   ```

## What the exploration script does:

1. **🔍 Connection Test**: Verifies your token works with a simple `me` query
2. **📚 Schema Exploration**: Downloads the complete GraphQL schema to understand available queries
3. **🔍 Book Search Tests**: Tests book search and verification capabilities
4. **💾 Schema Export**: Saves the full schema to `hardcover_schema.json` for development reference
5. **🚀 API Discovery**: Explores available GraphQL queries and types

## Using the Production Client:

The `hardcover_client.py` provides a production-ready async GraphQL client:

```python
from hardcover_client import HardcoverClient

# Initialize client (requires HARDCOVER_API_TOKEN environment variable)
client = HardcoverClient()

# Search for books
books = await client.search_books("dune frank herbert", limit=5)

# Get book details
book = await client.get_book_by_id(12345)

# Get user recommendations
recommendations = await client.get_user_recommendations(limit=10)

# Get trending books
trending = await client.get_trending_books(
    from_date="2025-01-01",
    to_date="2025-01-31"
)

# Always close when done
await client.close()
```

## Expected Output from Exploration Script:

```
🚀 Hardcover API Explorer
==================================================
🔍 Testing Hardcover API connection...
📡 Status: 200
✅ Connected successfully!
   User: {'me': [{'id': 148, 'username': 'your_username', 'email': 'your_email'}]}

🔍 Exploring GraphQL schema...

📚 Available root queries in Query:
  • me: User
  • books: [Book]
  • search: SearchOutput
  • books_trending: TrendingOutput
  ...

📖 Book-related types:
  • Book (OBJECT)
    ◦ id: ID
    ◦ title: String
    ◦ description: String
    ◦ isbn13: String
    ◦ cached_contributors: String
    ...

💾 Full schema saved to 'hardcover_schema.json'
```

## Integration with Marty Bot:

The Hardcover client is designed to work with Claude AI for book recommendations:

1. **Claude AI** generates book recommendations based on user conversation
2. **Hardcover Client** verifies book existence and provides detailed metadata
3. **Discord Bot** combines both for rich, verified book recommendations
4. **Purchase Flow** uses Hardcover data for inventory and affiliate links

## Environment Configuration:

Add to your `.env` file (see `.env.example`):

```bash
# Hardcover API Configuration
HARDCOVER_API_TOKEN=Bearer your_hardcover_api_token_here
HARDCOVER_API_URL=https://api.hardcover.app/v1/graphql
HARDCOVER_TOKEN_EXPIRY=2026-07-11T15:42:27
```

## Token Management:

- **Expiry**: Your token expires on 7/11/2026, 3:42:27 PM
- **Security**: Keep your token private, never commit it to version control
- **Beta Status**: Tokens may be reset during beta without notice
- **Format**: Must include "Bearer " prefix

## Testing:

Run the comprehensive test suite:

```bash
# Run all Hardcover tests
uv run pytest tests/test_hardcover.py -v

# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=hardcover_client
```

## Troubleshooting:

- **401 Unauthorized**: Check your token format (needs "Bearer " prefix) and expiry
- **403 Forbidden**: Your account may not have access to certain data
- **GraphQL Errors**: Check field names against the schema (use exploration script)
- **SSL Warnings**: Fixed in production client with `ssl=True`
- **Import Errors**: Run `uv sync` to install all dependencies

## Development Workflow:

1. **Explore**: Use `scripts/explore_hardcover_api.py` to discover new API features
2. **Implement**: Add new methods to `hardcover_client.py`
3. **Test**: Add tests to `tests/test_hardcover.py`
4. **Document**: Update this file with new capabilities
