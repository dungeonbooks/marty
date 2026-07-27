#!/usr/bin/env python3
"""
Terminal chat interface to interact with Marty.
Quick way to test the AI without going through the full SMS pipeline.

FOR INTERNAL DEVELOPER TESTING ONLY - NOT FOR PRODUCTION USE
"""

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import colorama
import structlog
from colorama import Fore, Style
from dotenv import load_dotenv

# Initialize colorama for cross-platform color support
colorama.init()

# Load environment variables from .env file
load_dotenv()

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Create logs directory if it doesn't exist
(PROJECT_ROOT / "logs").mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(str(PROJECT_ROOT / "logs" / "chat.log")),
        logging.StreamHandler(),
    ],
)
logger = structlog.get_logger(__name__)


@dataclass
class ChatConfig:
    """Configuration for the chat interface."""

    max_history_length: int = 20
    api_key_env_var: str = "NEURALWATT_API_KEY"
    default_customer_name: str = "Terminal User"
    default_phone: str = "+1555000000"
    default_customer_id: str = "test_user"
    commands: dict[str, str] = field(
        default_factory=lambda: {
            "quit": "Exit the chat",
            "exit": "Exit the chat",
            "clear": "Clear conversation history",
            "context": "Show current context",
            "help": "Show available commands",
            "save": "Save conversation history",
            "load": "Load conversation history",
        }
    )


class ChatError(Exception):
    """Base exception for chat-related errors."""

    pass


class APIKeyError(ChatError):
    """Raised when API key is missing or invalid."""

    pass


class MartyChat:
    """Enhanced terminal chat interface for Marty."""

    def __init__(self, config: ChatConfig | None = None):
        self.config = config or ChatConfig()
        self.conversation_history: list[Any] = []
        self.customer_context = self._initialize_context()

    def _initialize_context(self) -> dict[str, Any]:
        """Initialize customer context with current time information."""
        now = datetime.now(UTC)
        return {
            "name": self.config.default_customer_name,
            "phone": self.config.default_phone,
            "customer_id": self.config.default_customer_id,
            "current_time": now.isoformat(),
            "current_date": now.strftime("%Y-%m-%d"),
            "current_day": now.strftime("%A"),
        }

    def _update_time_context(self) -> None:
        """Update time-related context fields."""
        now = datetime.now(UTC)
        self.customer_context.update(
            {
                "current_time": now.isoformat(),
                "current_date": now.strftime("%Y-%m-%d"),
                "current_day": now.strftime("%A"),
            }
        )

    def _print_banner(self) -> None:
        """Print the chat banner."""
        banner = f"""
{Fore.CYAN}🧙 Marty Terminal Chat{Style.RESET_ALL}
{Fore.CYAN}{"=" * 40}{Style.RESET_ALL}
{Fore.YELLOW}Commands:{Style.RESET_ALL}
"""
        for cmd, desc in self.config.commands.items():
            banner += f"  {Fore.GREEN}{cmd}{Style.RESET_ALL}: {desc}\n"
        banner += f"{Fore.CYAN}{'=' * 40}{Style.RESET_ALL}"
        print(banner)

    def _print_context(self) -> None:
        """Print current context information."""
        print(f"\n{Fore.BLUE}📋 Current Context:{Style.RESET_ALL}")
        for key, value in self.customer_context.items():
            print(f"  {Fore.CYAN}{key}{Style.RESET_ALL}: {value}")

    def _print_help(self) -> None:
        """Print help information."""
        print(f"\n{Fore.BLUE}📖 Available Commands:{Style.RESET_ALL}")
        for cmd, desc in self.config.commands.items():
            print(f"  {Fore.GREEN}{cmd}{Style.RESET_ALL}: {desc}")

    def _validate_api_key(self) -> None:
        """Validate that the API key is available."""
        if not os.getenv(self.config.api_key_env_var):
            raise APIKeyError(
                f"❌ {self.config.api_key_env_var} not found in environment\n"
                f"Please set your Neuralwatt API key in .env file"
            )

    def _add_to_history(
        self, role: str, content: str, timestamp: datetime | None = None
    ) -> None:
        """Add a message to conversation history."""
        from src.ai_client import ConversationMessage

        if timestamp is None:
            timestamp = datetime.now(UTC)

        self.conversation_history.append(
            ConversationMessage(role=role, content=content, timestamp=timestamp)
        )

        # Trim history if it gets too long
        if len(self.conversation_history) > self.config.max_history_length:
            self.conversation_history = self.conversation_history[
                -self.config.max_history_length :
            ]

    def _handle_command(self, command: str) -> bool:
        """Handle special commands. Returns True if command was handled."""
        command_lower = command.lower()

        if command_lower in ["quit", "exit"]:
            print(f"\n{Fore.YELLOW}👋 Goodbye!{Style.RESET_ALL}")
            return True

        if command_lower == "clear":
            self.conversation_history = []
            print(f"\n{Fore.GREEN}🧹 Conversation history cleared!{Style.RESET_ALL}")
            return False

        if command_lower == "context":
            self._print_context()
            return False

        if command_lower == "help":
            self._print_help()
            return False

        if command_lower == "save":
            # TODO: Implement save functionality
            print(
                f"\n{Fore.YELLOW}💾 Save functionality not implemented yet{Style.RESET_ALL}"
            )
            return False

        if command_lower == "load":
            # TODO: Implement load functionality
            print(
                f"\n{Fore.YELLOW}📁 Load functionality not implemented yet{Style.RESET_ALL}"
            )
            return False

        return False

    async def _get_initial_response(self) -> str:
        """Get Marty's initial greeting."""
        from src.ai_client import generate_ai_response

        try:
            response, _ = await generate_ai_response(
                user_message="hello",
                conversation_history=[],
                customer_context=self.customer_context,
            )
            return response
        except Exception as e:
            logger.error(f"Failed to get initial response: {e}")
            raise ChatError(f"Failed to get initial response: {e}") from e

    async def _get_ai_response(self, user_input: str) -> str:
        """Get AI response for user input."""
        from src.ai_client import generate_ai_response

        try:
            response, _ = await generate_ai_response(
                user_message=user_input,
                conversation_history=self.conversation_history,
                customer_context=self.customer_context,
            )
            return response
        except Exception as e:
            logger.error(f"Failed to get AI response: {e}")
            raise ChatError(f"Failed to get AI response: {e}") from e

    async def start_chat(self) -> None:
        """Start the interactive chat session."""
        try:
            # Import after path setup

            self._print_banner()
            self._validate_api_key()

            # Get initial response
            print(f"\n{Fore.MAGENTA}🤔 Marty is thinking...{Style.RESET_ALL}")
            initial_response = await self._get_initial_response()
            print(f"\n{Fore.BLUE}🤖 Marty:{Style.RESET_ALL} {initial_response}")

            # Add initial greeting to history
            self._add_to_history("user", "hello")
            self._add_to_history("assistant", initial_response)

            # Main chat loop
            while True:
                try:
                    user_input = input(
                        f"\n{Fore.GREEN}👤 You:{Style.RESET_ALL} "
                    ).strip()

                    if not user_input:
                        continue

                    # Handle commands
                    if self._handle_command(user_input):
                        break

                    # Update time context
                    self._update_time_context()

                    # Get AI response
                    print(f"\n{Fore.MAGENTA}🤔 Marty is thinking...{Style.RESET_ALL}")
                    response = await self._get_ai_response(user_input)

                    # Add to history
                    self._add_to_history("user", user_input)
                    self._add_to_history("assistant", response)

                    print(f"\n{Fore.BLUE}🤖 Marty:{Style.RESET_ALL} {response}")

                except KeyboardInterrupt:
                    print(f"\n\n{Fore.YELLOW}👋 Goodbye!{Style.RESET_ALL}")
                    break
                except ChatError as e:
                    print(f"\n{Fore.RED}❌ Chat Error: {e}{Style.RESET_ALL}")
                    print(
                        f"{Fore.YELLOW}Try again or type 'quit' to exit{Style.RESET_ALL}"
                    )
                except Exception as e:
                    logger.error(f"Unexpected error in chat loop: {e}")
                    print(f"\n{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}")
                    print(
                        f"{Fore.YELLOW}Try again or type 'quit' to exit{Style.RESET_ALL}"
                    )

        except APIKeyError as e:
            print(f"\n{Fore.RED}{e}{Style.RESET_ALL}")
            return
        except Exception as e:
            logger.error(f"Failed to start chat: {e}")
            print(f"\n{Fore.RED}❌ Failed to start chat: {e}{Style.RESET_ALL}")
            return


async def main() -> None:
    """Main entry point."""
    try:
        config = ChatConfig()
        chat = MartyChat(config)
        await chat.start_chat()
    except Exception as e:
        logger.error(f"Failed to run chat: {e}")
        print(f"{Fore.RED}❌ Failed to run chat: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
