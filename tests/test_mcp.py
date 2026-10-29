import asyncio
from contextlib import AsyncExitStack
import json
from pathlib import Path
import sys
import tempfile
import unittest

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    ClientSession = None


def payload(result):
    if result.isError:
        raise AssertionError(result.content)
    return result.structuredContent or json.loads(result.content[0].text)


@unittest.skipUnless(ClientSession, "the packaged check supplies the official MCP SDK")
class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_independent_stdio_clients_exchange_messages(self):
        with tempfile.TemporaryDirectory() as directory:
            async with AsyncExitStack() as stack:
                clients = []
                for name in ("system", "blackbox", "zenlink"):
                    parameters = StdioServerParameters(
                        command=sys.executable,
                        args=[str(Path(__file__).resolve().parents[1] / "agent_chat.py")],
                        env={"AGENT_CHAT_DB": str(Path(directory) / "messages.sqlite"),
                             "CODEX_THREAD_ID": name},
                    )
                    reader, writer = await stack.enter_async_context(stdio_client(parameters))
                    client = await stack.enter_async_context(ClientSession(reader, writer))
                    await client.initialize()
                    names = {tool.name for tool in (await client.list_tools()).tools}
                    self.assertEqual({"register", "agents", "send", "read", "wait"}, names)
                    payload(await client.call_tool("register", {"name": name}))
                    clients.append(client)
                a, b, c = clients
                self.assertEqual(3, len(payload(await a.call_tool("agents", {}))["agents"]))
                waiting = asyncio.create_task(b.call_tool("wait", {"timeout": 3}))
                await asyncio.sleep(0.1)
                sent = payload(await a.call_tool("send", {"text": "shared pin change", "to": "blackbox"}))
                received = payload(await asyncio.wait_for(waiting, 5))
                self.assertEqual(sent["message_id"], received["messages"][0]["id"])
                self.assertFalse(received["timed_out"])
                self.assertEqual([], payload(await c.call_tool("read", {"after_id": 0}))["messages"])
                payload(await a.call_tool("send", {"text": "build finished"}))
                public = payload(await c.call_tool("read", {}))["messages"]
                self.assertEqual("build finished", public[0]["text"])
                invalid = await a.call_tool("wait", {"timeout": 61})
                self.assertTrue(invalid.isError)


if __name__ == "__main__":
    unittest.main()
