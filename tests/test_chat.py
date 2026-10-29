import asyncio
from pathlib import Path
import tempfile
import unittest

from agent_chat import Chat


class ChatTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.database = Path(self.temporary.name) / "chat/messages.sqlite"
        self.a, self.b, self.c = [Chat(self.database) for _ in range(3)]
        for name, chat in zip(("system", "blackbox", "zenlink"), (self.a, self.b, self.c)):
            chat.register(name, f"/Projects/{name}", session_id=name)
            self.addCleanup(chat.close)

    async def test_wait_receives_another_clients_message(self):
        pending = asyncio.create_task(self.b.wait(timeout=2))
        await asyncio.sleep(0.05)
        sent = self.a.send("Updating the shared lockfile")
        result = await pending
        self.assertFalse(result["timed_out"])
        self.assertEqual(sent["message_id"], result["messages"][0]["id"])
        self.assertEqual("system", result["messages"][0]["sender"])
        self.assertEqual([], self.b.read()["messages"])

    async def test_direct_messages_do_not_leak_to_other_agents(self):
        self.a.send("private coordination", to="blackbox")
        self.assertEqual([], self.c.read(after_id=0)["messages"])
        self.assertEqual("private coordination", self.b.read()["messages"][0]["text"])
        self.assertEqual("private coordination", self.a.read(after_id=0)["messages"][0]["text"])

    async def test_channels_have_independent_cursors(self):
        self.a.send("other room", channel="builds")
        self.a.send("common room")
        self.assertEqual("common room", self.b.read()["messages"][0]["text"])
        self.assertEqual("other room", self.b.read(channel="builds")["messages"][0]["text"])

    async def test_reconnection_keeps_identity_and_unread_cursor(self):
        first_id = self.b.agent_id
        self.a.send("already read", to="blackbox")
        self.b.read()
        self.a.send("not read yet", to="blackbox")
        self.b.close()
        resumed = Chat(self.database)
        self.addCleanup(resumed.close)
        self.assertEqual(first_id, resumed.register("blackbox", session_id="blackbox")["agent_id"])
        self.assertEqual(["not read yet"], [m["text"] for m in resumed.read()["messages"]])

    async def test_name_collision_requires_agent_id(self):
        self.c.register("blackbox", session_id="zenlink")
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.a.send("hello", to="blackbox")
        self.a.send("hello", to=self.b.agent_id)
        self.assertEqual("hello", self.b.read()["messages"][0]["text"])

    async def test_disconnected_peers_are_not_offered_as_connected(self):
        self.c.close()
        self.assertEqual({"system", "blackbox"}, {a["name"] for a in self.a.agents()})

    async def test_timeout_and_argument_validation(self):
        self.assertTrue((await self.b.wait(timeout=0.02))["timed_out"])
        with self.assertRaises(ValueError):
            await self.b.wait(timeout=61)
        with self.assertRaises(ValueError):
            self.a.send("")
        with self.assertRaises(ValueError):
            self.b.read(after_id=-1)
        self.assertEqual(0o600, self.database.stat().st_mode & 0o777)

    async def test_cancelled_wait_releases_the_cursor_lock(self):
        pending = asyncio.create_task(self.b.wait(timeout=60))
        await asyncio.sleep(0.02)
        pending.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await pending
        self.assertFalse(self.b.lock.locked())
        self.a.send("work can continue")
        self.assertEqual("work can continue", (await self.b.wait(timeout=0))["messages"][0]["text"])


if __name__ == "__main__":
    unittest.main()
