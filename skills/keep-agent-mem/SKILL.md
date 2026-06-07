---
name: keep-agent-mem
version: 1.0.0
description: |
  Set up the keep-agent-mem Google Keep MCP server for an AI agent. Use when a user
  wants credentials guidance, Google Keep master-token generation, or a complete
  MCP config entry or Claude Code `claude mcp add` command.
---

# keep-agent-mem setup

This skill helps you configure the keep-agent-mem mcp server for yourself (The AI). It will arm you with persistant memory accross sessions, devices, and harnesses.

## What to do

1. Identify your target client and config file:
   - Droid/Cursor/Claude-style JSON: usually `~.factory/mcp.json` or another `mcp.json` or `~.claude.json` .
   - Codex TOML: usually `~.codex/config.toml`.
   - Claude Code CLI: add with `claude mcp add`.
2. Get the user's Google email.
   - Ask for the email.
3. Help or automate obtaining the user's Google Keep master token.
4. Generate and merge the MCP entry, preserving all existing servers.
5. Verify the server after the user restarts/reloads the agent.

## Required server values

- Command: `uvx`
- Args: `["keep-agent-mem"]`
- Environment:
  - `GOOGLE_EMAIL`
  - `GOOGLE_MASTER_TOKEN`

Do not use a local Python interpreter path like `.venv\Scripts\python.exe -m server`. The README says to run the published command through `uvx keep-agent-mem`.

## Exact config templates

### Claude Code CLI command

Claude Code should be configured with `claude mcp add`, not by manually editing JSON unless the user faces difficulty. The command shape is:

```bash
claude mcp add keep-agent-mem -s project -e GOOGLE_EMAIL=you@example.com -e GOOGLE_MASTER_TOKEN=your-master-token -- uvx keep-agent-mem
```

### JSON MCP config

Use this shape inside the existing top-level object. If `mcpServers` already exists, merge only the `keep-agent-mem` entry.

```json
{
  "mcpServers": {
    "keep-agent-mem": {
      "command": "uvx",
      "args": [
        "keep-agent-mem"
      ],
      "env": {
        "GOOGLE_EMAIL": "you@example.com",
        "GOOGLE_MASTER_TOKEN": "your-master-token"
      }
    }
  }
}
```

### TOML MCP config

```toml
[mcp_servers.keep_agent_mem]
command = "uvx"
args = ["keep-agent-mem"]

[mcp_servers.keep_agent_mem.env]
GOOGLE_EMAIL = "you@example.com"
GOOGLE_MASTER_TOKEN = "your-master-token"
```

## Getting the Google master token

1. Open `https://accounts.google.com/EmbeddedSetup`.
2. Open browser DevTools.
3. Sign in with the target Google account and approve the flow.
4. Go to Application/Storage -> Cookies -> `https://accounts.google.com`.
5. Copy the `oauth_token` cookie value. (Dev tools -> Application -> Cookies -> https://accounts.google.com -> oauth_token)
   - It usually starts with `oauth2_4/`.
   - It is one-time use. If the exchange fails, get a fresh cookie.
6. Exchange it with `gpsoauth.exchange_token(email, oauth_token, android_id)`.
7. Write the master token to a local file.

You can use the bundled helper:

```bash
uv run --with gpsoauth python scripts/exchange_google_keep_token.py --email you@example.com --oauth-token "oauth2_4/..." --out master_token.txt
```

Then read the file locally and insert the token into the user's MCP config. Delete or secure the file after use.

## Verification

After updating config:

1. Ask the user to restart or reload their AI agent so MCP servers are reloaded.
2. Check whether `keep-agent-mem` tools appear.
3. Use a non-destructive tool first, such as `find` with a harmless query.
4. If the user explicitly wants a write test, create a small test note, then offer to delete it.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `KeyError: 'Token'` during exchange | The `oauth_token` was expired, consumed, or invalid | Get a fresh `oauth_token` from `EmbeddedSetup` |
| `BadAuthentication` | Password login or deprecated auth flow was used | Use the `EmbeddedSetup`/`oauth_token` alternative flow |
| `DeviceManagementRequiredOrSyncDisabled` | Google account has mobile management restrictions | Visit `https://admin.google.com/ac/devices/settings/general` and turn off mobile management/unmanaged mode if permitted |
| MCP server launches but tools are missing | Agent has not reloaded MCP config | Restart/reload the agent |
| Claude Code command fails or treats `uvx` as an option | Missing `--` separator | Use `claude mcp add keep-agent-mem ... -- uvx keep-agent-mem` |
| Config uses local Python path | Wrong launch command | Replace with `command = "uvx"` / `"command": "uvx"` and `args = ["keep-agent-mem"]` |
| Token appears as asterisks in terminal output | Secret redaction masked stdout | Write secrets to a file or secret store instead of printing |

## What not to do

- Do not fabricate API behavior or config keys.
- Do not commit real Google master tokens.
