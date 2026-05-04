"""get_doc tool: fetch a Dungeon Books doc page by slug."""

from typing import Any

from ..base import BaseTool, ToolResult
from .fetcher import DocNotFoundError, DocNotPublishedError, fetch_doc


class GetDocTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_doc"

    @property
    def description(self) -> str:
        return (
            "Fetch a Dungeon Books documentation page by slug. Use this to "
            "look up store policies, hours, location, event info, or order "
            "info before answering a customer's operational question. Pick "
            "the slug from the docs index in your system prompt. Examples: "
            "'store', 'events', 'orders', 'policies/event-ticket-policy', "
            "'policies/return-policy'. Returns markdown body plus any "
            "agent_guidance directives extracted from HTML comments — follow "
            "those directives when crafting the customer reply."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "slug": {
                "type": "string",
                "description": (
                    "Path-like slug from the docs index, no .md extension. "
                    "Examples: 'store', 'policies/event-ticket-policy'."
                ),
            }
        }

    async def execute(self, **kwargs) -> ToolResult:
        slug = (kwargs.get("slug") or "").strip().lstrip("/")
        if not slug:
            return ToolResult(success=False, data=None, error="slug is required")

        try:
            payload = await fetch_doc(slug)
        except DocNotFoundError:
            return ToolResult(
                success=False,
                data=None,
                error=f"No doc found at slug '{slug}'.",
            )
        except DocNotPublishedError:
            return ToolResult(
                success=False,
                data=None,
                error=f"Doc '{slug}' is not published.",
            )
        except Exception as e:
            self.logger.warning(f"get_doc fetch failed for slug={slug}: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Could not fetch doc '{slug}'.",
            )

        return ToolResult(
            success=True,
            data={
                "slug": payload.slug,
                "title": payload.frontmatter.get("title"),
                "body": payload.body,
                "agent_guidance": payload.agent_guidance,
            },
            metadata={
                "tags": payload.frontmatter.get("tags"),
                "date": payload.frontmatter.get("date"),
                "status": payload.frontmatter.get("status"),
            },
        )
