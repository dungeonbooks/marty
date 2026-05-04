#!/usr/bin/env python3
"""Alternative-provider sandbox for Marty's LLM path.

Production routes through Together (see scripts/chat.py and src/ai_client.py).
This script lets you swap to Fireworks / OpenRouter / Hugging Face for A/B
testing or as a manual failover smoke check, without touching prod code or
the production system prompt path.

All providers expose OpenAI-compatible endpoints, so the only differences are
base URL, env var, and the model identifier slug.

Usage (Together, default):
    export TOGETHER_API_KEY=...
    uv run python scripts/chat_kimi.py

Switch provider:
    KIMI_PROVIDER=fireworks   FIREWORKS_API_KEY=...   uv run python scripts/chat_kimi.py
    KIMI_PROVIDER=openrouter  OPENROUTER_API_KEY=...  uv run python scripts/chat_kimi.py
    KIMI_PROVIDER=hf          HF_TOKEN=...            uv run python scripts/chat_kimi.py

Override model (e.g. K2.6 instead of default K2.5):
    KIMI_MODEL=accounts/fireworks/models/kimi-k2p6 KIMI_PROVIDER=fireworks \\
        uv run python scripts/chat_kimi.py

Pick non-reasoning variants. Reasoning variants stream a thinking trace
before the final answer (slow, leaky, not what we want in Discord).
"""

import asyncio
import os
import sys
from pathlib import Path

import colorama
from colorama import Fore, Style
from dotenv import load_dotenv
from openai import AsyncOpenAI

colorama.init()
load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SYSTEM_PROMPT_PATH = PROJECT_ROOT / "prompts" / "marty_system_prompt.md"

PROVIDERS: dict[str, dict[str, str]] = {
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "api_key_env": "TOGETHER_API_KEY",
        "default_model": "moonshotai/Kimi-K2.5",
    },
    "fireworks": {
        "base_url": "https://api.fireworks.ai/inference/v1",
        "api_key_env": "FIREWORKS_API_KEY",
        "default_model": "accounts/fireworks/models/kimi-k2-instruct",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": "moonshotai/kimi-k2",
    },
    "hf": {
        "base_url": "https://router.huggingface.co/v1",
        "api_key_env": "HF_TOKEN",
        "default_model": "moonshotai/Kimi-K2.5",
    },
}


async def main() -> None:
    provider = os.getenv("KIMI_PROVIDER", "together").lower()
    if provider not in PROVIDERS:
        print(
            f"{Fore.RED}unknown KIMI_PROVIDER='{provider}'. "
            f"valid: {', '.join(PROVIDERS)}{Style.RESET_ALL}"
        )
        sys.exit(1)

    config = PROVIDERS[provider]
    api_key = os.getenv(config["api_key_env"], "")
    base_url = config["base_url"]
    model = os.getenv("KIMI_MODEL", config["default_model"])

    if not api_key:
        print(
            f"{Fore.RED}{config['api_key_env']} not set in env or .env{Style.RESET_ALL}"
        )
        sys.exit(1)

    if not SYSTEM_PROMPT_PATH.exists():
        print(
            f"{Fore.RED}system prompt not found at {SYSTEM_PROMPT_PATH}"
            f"{Style.RESET_ALL}"
        )
        sys.exit(1)

    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    print(
        f"{Fore.CYAN}Marty (Kimi){Style.RESET_ALL}  "
        f"provider: {provider}  model: {model}"
    )
    print(f"{Fore.YELLOW}commands: 'quit' / 'clear' / Ctrl-D{Style.RESET_ALL}\n")

    history: list[dict] = [{"role": "system", "content": system_prompt}]

    while True:
        try:
            user_msg = input(f"{Fore.GREEN}you>{Style.RESET_ALL} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not user_msg:
            continue
        if user_msg.lower() in ("quit", "exit"):
            return
        if user_msg.lower() == "clear":
            history = [{"role": "system", "content": system_prompt}]
            print(f"{Fore.YELLOW}cleared{Style.RESET_ALL}\n")
            continue

        history.append({"role": "user", "content": user_msg})
        try:
            resp = await client.chat.completions.create(
                model=model,
                max_tokens=500,
                temperature=0.7,
                messages=history,
                # Kimi K2.5/K2.6 are hybrid reasoning models. Disable thinking
                # so content lands in `message.content` instead of being
                # written into `message.reasoning` and burning the token
                # budget before any answer is emitted.
                extra_body={"reasoning": {"enabled": False}},
            )
        except Exception as e:
            print(f"{Fore.RED}error: {e}{Style.RESET_ALL}\n")
            history.pop()
            continue

        text = (resp.choices[0].message.content or "").strip()
        history.append({"role": "assistant", "content": text})

        usage = resp.usage
        meta = ""
        if usage is not None:
            meta = (
                f"  {Fore.MAGENTA}[in={usage.prompt_tokens} "
                f"out={usage.completion_tokens}]{Style.RESET_ALL}"
            )
        print(f"\n{Fore.BLUE}marty>{Style.RESET_ALL} {text}{meta}\n")


if __name__ == "__main__":
    asyncio.run(main())
