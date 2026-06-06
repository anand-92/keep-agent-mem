# keep-agent-mem

MCP server for Google Keep that serves as cross-device memory for your agents.


## How to use

1. Add the MCP server to your MCP servers:

### `config.toml` clients (Claude, Droid, Cursor)

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

Check https://gkeepapi.readthedocs.io/en/latest/#obtaining-a-master-token and https://github.com/simon-weber/gpsoauth?tab=readme-ov-file#alternative-flow for more information.

## Tools

### Query and read tools
* `find`: Search notes with optional filters for labels, colors, pinned, archived, and trashed
* `get`: Get a single note by ID

### Creation, update, and deletion tools
* `create`: Create a new note with a title, text, and an associated label
* `update`: Update a note's title and text
* `delete`: Delete a note by ID




## Troubleshooting

* If you get "DeviceManagementRequiredOrSyncDisabled" check https://admin.google.com/ac/devices/settings/general and turn "Turn off mobile management (Unmanaged)"
