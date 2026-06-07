# AGENTS.md

Context for AI agents working on **keep-agent-mem**: an MCP (Model Context Protocol)
server that exposes Google Keep as cross-device, persistent memory for other agents.

## What it does

Agents call MCP tools (`list_notes`, `create`, `update`, `delete`) to read/write
notes in a user's Google Keep account. Each note is tagged with a **label** (the
project/repo name) so memory is scoped per project. Transport is **stdio** — the
process is launched by an MCP client (Claude, Codex, Goose, etc.) via `uvx keep-agent-mem`.

## Architecture

```
MCP client (LLM agent)
      │  stdio / JSON-RPC
      ▼
src/server/cli.py        ← FastMCP app + @mcp.tool() definitions (tool layer)
      │
      ▼
src/server/keep_api.py   ← gkeepapi auth, client caching, note serialization
      │
      ▼
Google Keep (via gkeepapi, unofficial API)
```

- **`src/server/cli.py`** — the heart of the server. Defines the `FastMCP("keep")`
  instance and all MCP tools. Each tool's docstring **is the schema/description the
  agent sees** — edit docstrings carefully, they drive tool-calling behavior. Helpers:
  `_get_note_or_raise` (fetch + 404), `_normalize_colors` (string → `gkeepapi.node.ColorValue`).
- **`src/server/keep_api.py`** — `get_client()` authenticates once and caches a module-global
  `_keep_client`, calling `keep.sync()` on reuse. `serialize_note()` flattens a Keep note into
  a plain dict (id, title, text, type, pinned/archived/trashed, color, labels, collaborators,
  list items, media blobs).
- **`src/server/__main__.py`** — enables `python -m server`; just calls `cli.main()`.
- **`scripts/smoke_test.py`** — manual real-account lifecycle check (not run in CI).

## Key behaviors / gotchas

- **Auth**: requires env vars `GOOGLE_EMAIL` and `GOOGLE_MASTER_TOKEN` (master token, not
  password — see README). Missing creds → `ValueError` at first client use. Loaded via
  `python-dotenv` (`.env` supported locally; see `.example.env`).
- **Client is a cached singleton** (`_keep_client`). Tests reset it with
  `keep_api._keep_client = None` and monkeypatch `get_client`.
- **Every mutation must call `keep.sync()`** to push changes to Google — `create`/`update`/
  `delete` do this. Forgetting `sync()` silently drops the write.
- **Labels auto-create**: `create` looks up the label by name and creates it if missing.
- **Colors** are validated/normalized; invalid color string → `ValueError("Invalid color ...")`.
- The gkeepapi backend is **unofficial**; auth can fail with `DeviceManagementRequiredOrSyncDisabled`
  or non-JSON 4xx responses — `get_client()` wraps these in descriptive `RuntimeError`s.

## Adding a new MCP tool

1. Add a function in `cli.py` decorated with `@mcp.tool()`.
2. Write a precise docstring + typed args — this becomes the agent-facing schema.
3. Use `get_client()` for the Keep handle and `_get_note_or_raise` when operating on an id.
4. Call `keep.sync()` after any mutation; return `serialize_note(...)` for note results.
5. Add a unit test (mock with `DummyKeep`) and an integration test via `fastmcp.client.Client`.

## Project layout

```
src/server/      MCP server package (entry point: server.cli:main)
tests/           pytest suite (conftest adds src/ to path; DummyKeep mocks gkeepapi)
scripts/         manual smoke test
.github/workflows/  CI (lint + test on py3.10–3.12) and release
pyproject.toml   deps, scripts, ruff + pytest config
```

Tests run fully offline using in-memory `DummyKeep`/`DummyNote` fakes — never hit the
real Google API in unit/integration tests.

## Commands — MANDATORY before EVERY commit/push

You **MUST** run all three and they **MUST** pass (lint clean, format clean,
tests green) before committing or pushing. No exceptions. Do not ask — just run them.

```bash
uv run ruff format .           # format (this WRITES files — always run, then stage the changes)
uv run ruff check .            # lint
uv run pytest -q               # tests
```

`ruff format .` rewrites files: run it first, then `git add` the result so the commit
is already formatted. Never push without a clean `ruff format --check .`.

CI gate: `ruff check .` must pass and coverage must stay ≥ 70%
(`pytest --cov=src/server --cov-fail-under=70`).
