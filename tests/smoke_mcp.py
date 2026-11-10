"""MCP stdio smoke: spawn the server as a real MCP client would and
call two tools live.

Run: python tests/smoke_mcp.py

The MCP stdio client spawns the server with a MINIMAL environment
(HOME, LOGNAME, PATH, SHELL, TERM, USER only). On this VM, outbound
HTTPS goes through an egress proxy, so the proxy/CA variables must
be passed explicitly or the server's requests are reset mid-TLS
(curl 35). This script forwards just those variables from the
current process environment (values are never written to the repo);
on a normal machine with direct internet they are simply absent
and the server works without them.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_PROXY_VARS = (
    "https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY",
    "CURL_CA_BUNDLE", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE",
    "no_proxy", "NO_PROXY",
)


async def main() -> int:
    env = {k: os.environ[k] for k in _PROXY_VARS if k in os.environ}
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "bim_mcp.server"],
        env=env or None,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            tools = await s.list_tools()
            names = [t.name for t in tools.tools]
            print("tools:", names)
            assert "bim_list_aktuel_dates" in names
            assert "bim_aktuel_products" in names
            r = await s.call_tool("bim_list_aktuel_dates", {})
            d = json.loads(r.content[0].text)
            assert "error" not in d, d
            print(f"dates: {d['count']} periods, first={d['dates'][0]}")
            r = await s.call_tool(
                "bim_aktuel_products",
                {"query": "yağ", "sort": "price_asc", "limit": 3},
            )
            d = json.loads(r.content[0].text)
            assert "error" not in d, d
            print("products (yağ):", [(p["name"], p["price_try"]) for p in d["products"]])
            r = await s.call_tool("bim_health", {})
            d = json.loads(r.content[0].text)
            print("health:", d["status"])
            assert d["status"] == "ok", d
    print("MCP stdio smoke: OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
