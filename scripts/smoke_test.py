#!/usr/bin/env python3
"""
Comprehensive smoke test for Marty's critical integrations.
Verifies Claude AI, Hardcover API, and database connectivity.

⚠️  WARNING: This test makes REAL API calls to Claude AI and Hardcover API
    which may incur costs. Use sparingly in development.
"""

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class SmokeTestError(Exception):
    """Smoke test specific error."""

    pass


class SmokeTestRunner:
    """Comprehensive smoke test runner."""

    def __init__(self):
        self.results = []
        self.failed_tests = []

    def _log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result."""
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")

        self.results.append({"test": test_name, "success": success, "message": message})

        if not success:
            self.failed_tests.append(test_name)

    async def test_environment_variables(self) -> bool:
        """Test that required environment variables are set."""
        required_vars = ["TOGETHER_API_KEY", "HARDCOVER_API_TOKEN", "DATABASE_URL"]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            self._log_test(
                "Environment Variables", False, f"Missing: {', '.join(missing_vars)}"
            )
            return False

        self._log_test("Environment Variables", True, "All required vars present")
        return True

    async def test_llm_integration(self) -> bool:
        """Test LLM integration (Together / Kimi K2.5)."""
        # Only run real API tests if explicitly enabled
        if not os.getenv("MARTY_ENABLE_REAL_API_TESTS"):
            self._log_test(
                "LLM",
                True,
                "Skipped (use MARTY_ENABLE_REAL_API_TESTS=1 to test real API)",
            )
            return True

        try:
            from src.ai_client import ConversationMessage, generate_ai_response

            # Test basic response
            response, _ = await generate_ai_response("Hello", [])
            if not response or len(response) < 5:
                raise SmokeTestError("Response too short or empty")

            # Test with conversation history
            history = [
                ConversationMessage(
                    role="user", content="Hello", timestamp=datetime.now(UTC)
                )
            ]

            response2, _ = await generate_ai_response("What's your name?", history)
            if not response2:
                raise SmokeTestError("No response with history")

            self._log_test("LLM", True, f"Response: {response[:30]}...")
            return True

        except Exception as e:
            self._log_test("LLM", False, str(e))
            return False

    async def test_hardcover_integration(self) -> bool:
        """Test Hardcover API integration."""
        try:
            from src.tools.external.hardcover import HardcoverTool

            tool = HardcoverTool()

            # Test authentication
            user_result = await tool.execute(action="get_current_user")
            if not user_result.success or not user_result.data.get("me"):
                raise SmokeTestError("Authentication failed")

            # Test book search
            books_result = await tool.execute(
                action="search_books", query="harry potter", limit=2
            )
            if not books_result.success or not books_result.data:
                raise SmokeTestError("Book search returned no results")

            await tool.close()

            username = user_result.data.get("me", {}).get("username", "Unknown")
            self._log_test(
                "Hardcover API",
                True,
                f"User: {username}, Found {len(books_result.data)} books",
            )
            return True

        except Exception as e:
            self._log_test("Hardcover API", False, str(e))
            return False

    async def test_database_connection(self) -> bool:
        """Test database connectivity."""
        try:
            from sqlalchemy import text

            from src.database import AsyncSession, engine

            async with AsyncSession(engine) as session:
                # Test basic connection
                result = await session.execute(text("SELECT 1 as test"))
                test_value = result.scalar()

                if test_value != 1:
                    raise SmokeTestError("Database query failed")

            self._log_test("Database", True, "Connection successful")
            return True

        except Exception as e:
            self._log_test("Database", False, str(e))
            return False

    async def test_complete_flow(self) -> bool:
        """Test a complete conversation flow."""
        try:
            from src.ai_client import generate_ai_response
            from src.database import (
                AsyncSession,
                ConversationCreate,
                CustomerCreate,
                create_conversation,
                create_customer,
                engine,
            )

            # Create test customer
            async with AsyncSession(engine) as session:
                customer_data = CustomerCreate(
                    phone="+1555000000", name="Test User", square_customer_id=None
                )
                customer = await create_customer(session, customer_data)

                conversation_data = ConversationCreate(
                    customer_id=customer.id, phone=customer.phone
                )
                await create_conversation(session, conversation_data)

            # Generate AI response
            response, _ = await generate_ai_response(
                "recommend a fantasy book",
                [],
                customer_context={
                    "name": "Test User",
                    "phone": "+1555000000",
                    "customer_id": str(customer.id),
                    "current_time": datetime.now(UTC).isoformat(),
                    "current_date": datetime.now(UTC).strftime("%Y-%m-%d"),
                    "current_day": datetime.now(UTC).strftime("%A"),
                },
            )

            if not response:
                raise SmokeTestError("No AI response generated")

            self._log_test(
                "Complete Flow", True, f"Customer: {customer.id}, Response generated"
            )
            return True

        except Exception as e:
            self._log_test("Complete Flow", False, str(e))
            return False

    async def run_all_tests(self) -> bool:
        """Run all smoke tests."""
        print("🔍 Marty Smoke Test Suite")
        print("=" * 50)

        # Test environment
        env_ok = await self.test_environment_variables()
        if not env_ok:
            print("\n❌ Environment check failed - stopping tests")
            return False

        # Test individual components
        tests = [
            self.test_llm_integration(),
            self.test_hardcover_integration(),
            self.test_database_connection(),
            self.test_complete_flow(),
        ]

        # Run tests concurrently where possible
        results = await asyncio.gather(*tests, return_exceptions=True)

        # Count successful tests
        successful_tests = sum(1 for r in results if r is True)
        total_tests = len(results) + 1  # +1 for environment test

        print("\n" + "=" * 50)
        print(f"📊 Test Results: {successful_tests}/{total_tests} passed")

        if self.failed_tests:
            print(f"❌ Failed tests: {', '.join(self.failed_tests)}")
            return False

        print("🎉 All smoke tests PASSED - Marty is ready!")
        return True


async def main():
    """Run smoke tests."""
    runner = SmokeTestRunner()
    success = await runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
