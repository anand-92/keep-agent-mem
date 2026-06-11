# keep-agent-mem

MCP server for Google Keep that serves as cross-device memory for your agents.


## How to use

The easiest way to get set up is to give your agent the onboarding skill and let it guide you through the rest:

1. Give the skill to your agent. If your agent supports installing skills directly, install this repository's skill:

```bash
npx skills add anand-92/keep-agent-mem
```

If not, share the contents of [`skills/keep-agent-mem/SKILL.md`](skills/keep-agent-mem/SKILL.md) with your agent.

2. Ask your agent to set up keep-agent-mem and guide you through getting credentials, for example:

> "Set up keep-agent-mem for me."

The skill walks the agent through obtaining your Google Keep master token, merging the MCP config entry, and verifying the server.

## Manual setup

If you'd rather configure it yourself:

1. Add the MCP server to your MCP servers:

```json
  "mcpServers": {
    "keep-agent-mem": {
      "command": "uvx",
      "args": [
        "keep-agent-mem"
      ],
      "env": {
        "GOOGLE_EMAIL": "Your Google Email",
        "GOOGLE_MASTER_TOKEN": "Your Google Master Token - see README.md"
      }
    }
  }
```

### `config.toml` clients (Codex, Goose, etc.)

```toml
[mcp_servers.keep_agent_mem]
command = "uvx"
args = ["keep-agent-mem"]

[mcp_servers.keep_agent_mem.env]
GOOGLE_EMAIL = "you@example.com"
GOOGLE_MASTER_TOKEN = "your-master-token"
```

2. Add your credentials:
* `GOOGLE_EMAIL`: Your Google account email address
* `GOOGLE_MASTER_TOKEN`: Your Google account master token

For credential setup, give [`skills/keep-agent-mem/SKILL.md`](skills/keep-agent-mem/SKILL.md) to your agent and ask it to guide you. The skill tells you to open `https://accounts.google.com/EmbeddedSetup`, copy the `oauth_token` cookie, and run the bundled exchange script to create your `GOOGLE_MASTER_TOKEN`:

```bash
uv run --with gpsoauth python scripts/exchange_google_keep_token.py --email you@example.com --oauth-token "oauth2_4/..." --out master_token.txt
```

Then put the token from `master_token.txt` into your MCP config and delete or secure the file after use.

## Tools

### Query and read tools
* `list_notes`: Search, list, and directly read notes with optional filters for note IDs, label IDs, label names, colors, pinned, archived, and trashed states. Defaults to `detail_level="summary"` with `limit=50` so agents do not pull unnecessary note content into context.

### Creation, update, and deletion tools
* `create`: Create a note or checklist/list note with one or more labels, initial metadata (`color`, `pinned`, `archived`), and optional duplicate handling via `dedupe_by` and `if_exists`.
* `update`: Update note title/body text, append or prepend text, add/remove labels, set metadata (`color`, `pinned`, `archived`, `trashed`), and guard writes with `expected_text_hash`.
* `delete`: Manage note lifecycle by ID. Defaults to safe `mode="trash"`; use `mode="restore"` to restore and `mode="delete", confirm=true` for permanent deletion.

### FastMCP-grounded design notes

This server intentionally keeps the same four-tool surface area while using FastMCP features to make those tools easier for agents and clients to reason about:

* Tool signatures use type annotations and enum-like `Literal` values so FastMCP can generate clearer input schemas.
* Tool return annotations are kept so FastMCP exposes structured content for machine-readable note results.
* Tool docstrings describe default behavior because FastMCP uses docstrings in tool descriptions.
* Tool annotations mark `list_notes` as read-only and mark mutating tools as external-system operations, helping clients apply better safety and confirmation UX.
* Tags group the tools by responsibilities such as `read`, `create`, `update`, `delete`, and `memory` for clients that expose or filter tagged tools.

Potential next improvements, still without adding more tools:

* Replace loose `dict` results with Pydantic/dataclass output models so FastMCP can publish more precise output schemas and clients can hydrate typed results.
* Use `Annotated`/`Field` parameter metadata for numeric constraints like `limit` and richer descriptions than plain type hints provide.
* Add FastMCP `meta` values for versioning and compatibility policy, making tool contract changes easier to inspect.
* Add stricter validation around incompatible argument combinations, such as `items` with `note_type="note"`, and expose those constraints in the generated schema where practical.
* Consider a future `resource` view for read-only memory snapshots if clients need cacheable project memory, while keeping writes in the existing tools.




## Troubleshooting

* If you get "DeviceManagementRequiredOrSyncDisabled" check https://admin.google.com/ac/devices/settings/general and turn "Turn off mobile management (Unmanaged)"
