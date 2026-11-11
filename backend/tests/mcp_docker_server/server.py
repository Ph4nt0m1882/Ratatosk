import os
import socket

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("ratatosk-docker-mcp")


@mcp.tool(description="Calculate the n-th Fibonacci number inside the Docker MCP container.")
def calculate_fibonacci(n: int) -> dict[str, int]:
    if n <= 0:
        return {"n": n, "fibonacci": 0}
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return {"n": n, "fibonacci": b}


@mcp.tool(description="Return container metadata and any MCP_TEST_TAG environment variable.")
def get_container_info(label: str = "ratatosk") -> dict[str, str]:
    return {
        "label": label,
        "hostname": socket.gethostname(),
        "tag": os.environ.get("MCP_TEST_TAG", "none"),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
