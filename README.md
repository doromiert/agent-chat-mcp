# Agent chat MCP

Local stdio MCP server for independent Codex sessions. Each session starts its
own process; processes exchange messages through the same SQLite mailbox. There
is no network listener or separate daemon. Data defaults to
`$XDG_STATE_HOME/agent-chat/messages.sqlite`, falling back to
`~/.private/State/agent-chat/messages.sqlite`. `AGENT_CHAT_DB` overrides that path.

Tools: `register`, `agents`, `send`, `read`, `wait`.

Register a name/project/task; pass your Codex thread ID as `session_id` to retain
identity and unread cursors across reconnects. Registration returns recent
messages and connected peers. Broadcasts use `coordination` by default; `send`
can address a connected agent ID or unique name. `read` consumes unread messages,
or browses history when given `after_id`. `wait` holds a pending call for at most
60 seconds and returns when a matching message arrives. Separate channels have
separate cursors. Names are not authentication: this is for one local user's
cooperating sessions, and peer messages never grant user authorization.

Messages persist, but a finished agent does not wake automatically. An agent must
read or have a `wait` call pending. Already-running Codex sessions need to reload
the MCP server or resume after restarting before they can use newly added tools.

Build/install:

```sh
nix build --out-link "$HOME/.private/Packages/agent-chat-mcp"
codex mcp add agent-chat -- "$HOME/.private/Packages/agent-chat-mcp/bin/agent-chat-mcp"
```

Add `default-instructions.md` to `$CODEX_HOME/AGENTS.md` (preserving existing
instructions). Suggested MCP config: `startup_timeout_sec = 20` and
`tool_timeout_sec = 90`; `wait` remains capped at 60 seconds.

Tests: `python3 -m unittest discover -s tests -v`. The packaged check also runs
the stdio MCP integration tests when the official Python MCP SDK is available.
