"""Smoke test for the get_doc tool against the live dungeonbooks/docs repo."""

import asyncio

from src.tools.docs.fetcher import (
    DocNotFoundError,
    DocNotPublishedError,
    fetch_doc,
)
from src.tools.docs.get_doc import GetDocTool


async def main() -> None:
    print("=== fetcher.fetch_doc ===")
    for slug in [
        "index",
        "store",
        "policies/event-ticket-policy",
        "policies/return-policy",
    ]:
        try:
            payload = await fetch_doc(slug)
        except Exception as e:
            print(f"  {slug:42s} FAIL: {type(e).__name__}: {e}")
            continue
        print(
            f"  {slug:42s} OK  title={payload.frontmatter.get('title')!r:35s} "
            f"body={len(payload.body)}c guidance={len(payload.agent_guidance)}"
        )

    print()
    print("=== publish gate ===")
    try:
        await fetch_doc("events")
        print(
            "  events                                  FAIL: expected DocNotPublishedError"
        )
    except DocNotPublishedError:
        print(
            "  events                                  OK  raised DocNotPublishedError"
        )
    except Exception as e:
        print(
            f"  events                                  FAIL: {type(e).__name__}: {e}"
        )

    print()
    print("=== 404 path ===")
    try:
        await fetch_doc("does-not-exist")
        print(
            "  does-not-exist                          FAIL: expected DocNotFoundError"
        )
    except DocNotFoundError:
        print("  does-not-exist                          OK  raised DocNotFoundError")
    except Exception as e:
        print(
            f"  does-not-exist                          FAIL: {type(e).__name__}: {e}"
        )

    print()
    print("=== GetDocTool.execute ===")
    tool = GetDocTool()
    result = await tool.execute(slug="policies/event-ticket-policy")
    print(f"  success={result.success}")
    if not result.success:
        print(f"  error={result.error!r}")
    else:
        print(f"  title={result.data.get('title')!r}")
        print(f"  agent_guidance count={len(result.data.get('agent_guidance', []))}")
        if result.data.get("agent_guidance"):
            first = result.data["agent_guidance"][0].splitlines()[0:3]
            print("  first guidance preview:")
            for line in first:
                print(f"    {line}")

    print()
    print("=== GetDocTool draft slug ===")
    result = await tool.execute(slug="orders")
    print(f"  success={result.success} error={result.error!r}")


if __name__ == "__main__":
    asyncio.run(main())
