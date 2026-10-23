"""The one connection this agent holds: the AgentCore Gateway.

The gateway URL arrives as an environment variable set in
agentcore/agentcore.json. This gateway deliberately has no inbound authorizer
(the lesson of uc04 is what the gateway checks after the connection, not who
may connect). Tools and their schemas come from the gateway over MCP.
"""

import os
import logging
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

GATEWAY_MCP_URL = os.environ.get("GATEWAY_MCP_URL", "")


def get_streamable_http_mcp_client() -> MCPClient:
    """Returns an MCP Client compatible with Strands"""
    return MCPClient(lambda: streamablehttp_client(GATEWAY_MCP_URL))
