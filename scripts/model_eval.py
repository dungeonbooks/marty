"""Compare candidate models against Marty's prompt rules.

Marty's style rules are unusually literal - named banned words, banned
punctuation, a sentence cap - so adherence can be scored instead of eyeballed.
This runs a fixed set of prompts through each model via the real
`generate_ai_response` path (tools included) and counts violations.

Scores are a floor, not a verdict. They catch the mechanical rules; tone still
needs reading, so every response is dumped alongside the table.

    uv run python scripts/model_eval.py
    uv run python scripts/model_eval.py --models glm-5.2-short kimi-k2.6
    uv run python scripts/model_eval.py --runs 3 --out /tmp/eval.md
"""

import argparse
import asyncio
import re
import statistics
import time
from dataclasses import dataclass, field

from src import ai_client
from src.ai_client import generate_ai_response
from src.config import config

DEFAULT_MODELS = ["glm-5.2-short", "kimi-k2.6", "kimi-k2.6-fast"]

# Reasoning tokens count against max_tokens. kimi-k2.6 spends the whole 500-token
# production budget thinking and returns empty content, which the tool loop turns
# into the "having trouble" fallback. Give each model enough room to actually
# answer, otherwise the comparison measures the budget rather than the model.
BASE_MAX_TOKENS = 500
MODEL_MAX_TOKENS = {"kimi-k2.6": 1500}

# Both strings generate_ai_response returns when it cannot get a real answer:
# the first when the tool loop ends with empty content, the second when the call
# raised. Neither breaks a style rule, so both must be caught explicitly.
FALLBACK_REPLIES = (
    "I'm having trouble generating a response right now.",
    "sorry, brain's lagging. can you try again?",
)

# Each prompt targets rules the model could plausibly break.
PROMPTS: list[tuple[str, str]] = [
    ("greeting", "yo marty"),
    ("casual_rec", "gimme a fantasy rec, something weird"),
    ("book_details", "can you pull up details on Piranesi by Susanna Clarke"),
    ("recent_releases", "what came out recently"),
    ("stock_question", "do u have The Fifth Season in stock right now"),
    ("where_to_buy", "where can i buy Dungeon Crawler Carl"),
    ("store_hours", "what time do you close on sunday"),
    ("why_read", "why should i read Dune"),
    ("comparison", "how does Gideon the Ninth compare to Locked Tomb sequels"),
    ("tier_list", "rank the Green Bone Saga books"),
    ("mtg_card", "what does Lightning Bolt do"),
    ("long_explain", "explain appendix n to me, i've never heard of it"),
]

AI_VOCAB = [
    "delve",
    "leverage",
    "robust",
    "seamless",
    "comprehensive",
    "crucial",
    "vital",
    "essential",
    "realm",
    "embark",
    "unlock",
    "elevate",
    "harness",
    "foster",
    "transformative",
]
SUPERLATIVES = [
    "best",
    "ultimate",
    "perfect",
    "amazing",
    "incredible",
    "must-read",
    "game-changing",
    "unparalleled",
]
FILLER = [
    "it's worth noting",
    "essentially",
    "in essence",
    "at the end of the day",
    "that being said",
    "needless to say",
]

SMART_PUNCT = "—–‘’“”…"
NOT_X_BUT_Y = re.compile(r"\bnot (just )?[^.,;]{2,40}[,-] (but|it's)\b", re.I)
SENTENCE_SPLIT = re.compile(r"[.!?]+(?:\s|$)")
URL = re.compile(r"https?://\S+")


@dataclass
class Result:
    label: str
    model: str
    prompt: str
    text: str
    seconds: float
    tools: list[str]
    violations: list[str] = field(default_factory=list)
    cost: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0


def find_violations(text: str, label: str, tools: list[str]) -> list[str]:
    """Check a response against the rules the prompt states literally."""
    out = []
    low = text.lower()

    # Must come first: a failed generation breaks no style rule, so without this
    # it scores as clean and a broken model looks like the best-behaved one.
    if text.startswith("<error:") or any(f in text for f in FALLBACK_REPLIES):
        return ["no-answer"]

    for ch in SMART_PUNCT:
        if ch in text:
            out.append(f"smart-punctuation({ch!r})")
            break

    for word in AI_VOCAB:
        if re.search(rf"\b{re.escape(word)}\b", low):
            out.append(f"ai-vocab({word})")
    for word in SUPERLATIVES:
        if re.search(rf"\b{re.escape(word)}\b", low):
            out.append(f"superlative({word})")
    for phrase in FILLER:
        if phrase in low:
            out.append(f"filler({phrase})")

    if NOT_X_BUT_Y.search(text):
        out.append("not-x-but-y")
    if "!" in text:
        out.append("exclamation")
    if re.search(r"^\s*#{1,6}\s", text, re.M):
        out.append("markdown-header")
    if "|" in text and re.search(r"\|.*\|", text):
        out.append("markdown-table")
    if re.search(r"^\s*(-{3,}|\*{3,})\s*$", text, re.M):
        out.append("horizontal-rule")
    if re.search(r"(?<!\*)\*(?!\*)[^*\n]+\*(?!\*)", text):
        out.append("italics")

    sentences = [s for s in SENTENCE_SPLIT.split(text) if s.strip()]
    # Rule 2 allows going longer on book details.
    cap = 8 if label in {"book_details", "long_explain", "why_read"} else 5
    if len(sentences) > cap:
        out.append(f"too-long({len(sentences)}>{cap})")

    for url in URL.findall(text):
        if "hardcover.app" in url:
            out.append("hardcover-link")
        elif "dungeonbooks.com" not in url:
            out.append("book-url")

    # Rule 1: prose should read lowercase. Flag only heavy capitalisation, since
    # titles and proper nouns legitimately capitalise.
    words = re.findall(r"\b[A-Za-z][a-z]+\b", text)
    caps = [w for w in words if w[0].isupper()]
    if words and len(caps) / len(words) > 0.4:
        out.append("over-capitalised")

    if label == "stock_question" and re.search(
        r"\b(in stock|out of stock|we have it|not in stock)\b", low
    ):
        out.append("claims-inventory")
    if label == "casual_rec" and tools:
        out.append("tool-on-casual-rec")
    if label == "recent_releases" and not re.search(r"^\s*\d[.)]", text, re.M):
        out.append("recent-not-numbered")

    return out


class UsageTap:
    """Record per-request cost and tokens by wrapping the chat completion call.

    One prompt can span several requests (the tool loop), so cost is summed per
    prompt rather than read off a single response.
    """

    def __init__(self) -> None:
        self.cost = 0.0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self._original = ai_client.client.chat.completions.create

    def reset(self) -> None:
        self.cost = 0.0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def install(self) -> None:
        async def wrapper(**kwargs):
            response = await self._original(**kwargs)
            usage = getattr(response, "usage", None)
            if usage is not None:
                self.prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
                self.completion_tokens += getattr(usage, "completion_tokens", 0) or 0
            cost = getattr(response, "cost", None)
            if isinstance(cost, dict):
                self.cost += cost.get("request_cost_usd") or 0.0
            return response

        ai_client.client.chat.completions.create = wrapper

    def remove(self) -> None:
        ai_client.client.chat.completions.create = self._original


async def run_one(model: str, label: str, prompt: str, tap: UsageTap) -> Result:
    config.MARTY_MODEL = model
    config.MARTY_MAX_TOKENS = MODEL_MAX_TOKENS.get(model, BASE_MAX_TOKENS)
    tap.reset()
    start = time.perf_counter()
    try:
        text, tool_results = await generate_ai_response(prompt, [])
    except Exception as exc:  # noqa: BLE001 - surfaced in the report
        # Record real elapsed time: zeroing it drags the latency percentiles down
        # and makes a model that fails slowly look fast.
        return Result(
            label,
            model,
            prompt,
            f"<error: {exc}>",
            time.perf_counter() - start,
            [],
            ["no-answer"],
        )
    elapsed = time.perf_counter() - start
    tools = [t.get("tool_name", "?") for t in tool_results]
    return Result(
        label,
        model,
        prompt,
        text,
        elapsed,
        tools,
        find_violations(text, label, tools),
        tap.cost,
        tap.prompt_tokens,
        tap.completion_tokens,
    )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--out", default="model_eval_report.md")
    args = parser.parse_args()

    original = config.MARTY_MODEL
    original_tokens = config.MARTY_MAX_TOKENS
    results: list[Result] = []
    tap = UsageTap()
    tap.install()
    try:
        for model in args.models:
            for run in range(args.runs):
                for label, prompt in PROMPTS:
                    res = await run_one(model, label, prompt, tap)
                    results.append(res)
                    flag = "!" if res.violations else " "
                    print(
                        f"{flag} {model:18} {label:16} {res.seconds:5.1f}s "
                        f"{len(res.violations)} violations"
                    )
                if run + 1 < args.runs:
                    print(f"--- {model} run {run + 2}/{args.runs} ---")
    finally:
        config.MARTY_MODEL = original
        config.MARTY_MAX_TOKENS = original_tokens
        tap.remove()

    write_report(results, args.models, args.out)


def write_report(results: list[Result], models: list[str], path: str) -> None:
    lines = [
        "# Model comparison",
        "",
        "## Summary",
        "",
        "| model | responses | violations | clean | median s | p90 s | $/reply | out tok |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for model in models:
        rows = [r for r in results if r.model == model]
        if not rows:
            continue
        times = sorted(r.seconds for r in rows)
        p90 = times[min(len(times) - 1, int(len(times) * 0.9))]
        total = sum(len(r.violations) for r in rows)
        clean = sum(1 for r in rows if not r.violations)
        avg_cost = statistics.mean(r.cost for r in rows)
        avg_out = statistics.mean(r.completion_tokens for r in rows)
        lines.append(
            f"| {model} | {len(rows)} | {total} | {clean}/{len(rows)} | "
            f"{statistics.median(times):.1f} | {p90:.1f} | "
            f"${avg_cost:.6f} | {avg_out:.0f} |"
        )

    lines += [
        "",
        "## Violations by kind",
        "",
        "| kind | " + " | ".join(models) + " |",
        "| --- |" + " --- |" * len(models),
    ]
    kinds = sorted({v.split("(")[0] for r in results for v in r.violations})
    for kind in kinds:
        counts = [
            str(
                sum(
                    1
                    for r in results
                    if r.model == m and any(v.startswith(kind) for v in r.violations)
                )
            )
            for m in models
        ]
        lines.append(f"| {kind} | " + " | ".join(counts) + " |")

    lines += ["", "## Responses", ""]
    for label, prompt in PROMPTS:
        lines += [f"### {label}", "", f"> {prompt}", ""]
        for model in models:
            for r in [x for x in results if x.model == model and x.label == label]:
                bad = ", ".join(r.violations) or "clean"
                tools = ", ".join(r.tools) or "none"
                lines += [
                    f"**{model}** ({r.seconds:.1f}s, tools: {tools}) - {bad}",
                    "",
                    "```",
                    r.text,
                    "```",
                    "",
                ]

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    asyncio.run(main())
