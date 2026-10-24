import os
import logging
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)


def get_research_gateway_mcp_client() -> MCPClient | None:
    """Returns an MCP Client connected to the research-gateway gateway."""
    url = os.environ.get("AGENTCORE_GATEWAY_RESEARCH_GATEWAY_URL")
    if not url:
        logger.warning("AGENTCORE_GATEWAY_RESEARCH_GATEWAY_URL not set — research-gateway gateway tools unavailable")
        return None
    return MCPClient(lambda: streamablehttp_client(url), prefix="research_gateway")
    
def get_all_gateway_mcp_clients() -> list[MCPClient]:
    """Returns MCP clients for all configured gateways."""
    clients = []
    client = get_research_gateway_mcp_client()
    if client:
        clients.append(client)
    return clients
