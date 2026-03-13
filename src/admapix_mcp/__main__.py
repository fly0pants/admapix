"""Entry point for `python -m admapix_mcp` and `admapix-mcp` CLI."""

from admapix_mcp.server import mcp_server


def main():
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
