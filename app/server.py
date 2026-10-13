"""Production ASGI entry point: existing API plus authenticated MCP endpoint."""
from app.main import app
from app.mcp_server import mount_mcp

mount_mcp(app)
