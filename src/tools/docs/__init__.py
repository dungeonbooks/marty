"""Operational documentation lookup tools.

Fetches markdown from the public dungeonbooks/docs repo and exposes it to
Claude as a tool. See https://github.com/dungeonbooks/docs.
"""

from .get_doc import GetDocTool

__all__ = ["GetDocTool"]
