from fastmcp import FastMCP

mcp = FastMCP("local")

@mcp.tool
def get_weather(city: str) -> str:
        """Get the current weather for a city."""
        # This is a placeholder implementation. In a real implementation, you would call a weather API.
        return f"The current weather in {city} is sunny with a temperature of 25°C."

if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)