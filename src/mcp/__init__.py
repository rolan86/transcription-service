"""
MCP (Model Context Protocol) server for the transcription service.
Exposes transcription tools for use by AI agents like Claude.
"""

from .server import mcp

__all__ = ["mcp"]
