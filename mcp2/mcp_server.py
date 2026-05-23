from fastmcp import FastMCP
from pydantic import BaseModel, Field

# 1. Initialize the MCP Server
# This replaces FastAPI as the routing layer for agentic interactions.
mcp = FastMCP("EquinixDataCenter")

# 2. Define Strict Context Schemas
# A 2026 production-quality tool must include strict type validation using Pydantic
class ServerRequest(BaseModel):
    server_id: str = Field(description="The unique identifier for the hardware node.")
    size_u: int = Field(description="The physical footprint in Rack Units (U).")
    rack_id: str = Field(description="The identifier of the rack where the server will be deployed.")

# 3. Expose the Tool to the LLM
# The docstring is critical: it tells the agent exactly when (and when not) to use this tool.
@mcp.tool()
def deploy_bare_metal(server_id: str, size_u: int, rack_id: str) -> str:
    """
    Deploys a new bare metal server to a specific rack in the data center.
    DO NOT use this tool if the user is only asking for rack capacity.
    """
    # In a real app, this would hit the Equinix Metal API
    return f"Success: Provisioning workflow started for {server_id} ({size_u}U) in rack {rack_id}."

@mcp.tool()
def get_rack_capacity(rack_id: str) -> str:
    """Retrieves the currently available physical capacity of a server rack."""
    return f"Rack {rack_id} has 42U available."

@mcp.resource("rack://{rack_id}/telemetry")
def get_rack_telemetry(rack_id: str) -> str:
    """Live temperature and power telemetry for a specific server rack."""
    # In a real data center, this queries the physical sensors
    if rack_id == "node-99":
        return f"Rack {rack_id} | Temp: 38C (CRITICAL) | Power: 8.5kW | Fan Speed: 100%"
    return f"Rack {rack_id} | Temp: 22C (NORMAL) | Power: 4.2kW | Fan Speed: 40%"

# 4. The MCP 2.0 Transport Upgrade
if __name__ == "__main__":
    # By specifying transport="sse", we enable standard SSE.
    mcp.run(transport="sse", host="0.0.0.0", port=8080)
