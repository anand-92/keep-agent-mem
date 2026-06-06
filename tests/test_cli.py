import pytest
from fastmcp.client import Client

from server import cli


class DummyLabel:
    def __init__(self, label_id="l1", name="keep-agent-mem"):
        self.id = label_id
        self.name = name


class DummyLabels:
    def __init__(self):
        self._labels = []

    def add(self, label):
        self._labels.append(label)

    def remove(self, label):
        self._labels = [existing for existing in self._labels if existing.id != label.id]

    def all(self):
        return self._labels


class DummyCollaborators:
    def __init__(self):
        self._emails = []

    def all(self):
        return list(self._emails)

    def add(self, email):
        self._emails.append(email)

    def remove(self, email):
        self._emails = [value for value in self._emails if value != email]


class DummyBlobType:
    def __init__(self, value="IMAGE"):
        self.value = value


class DummyBlobInner:
    def __init__(self):
        self.type = DummyBlobType("IMAGE")


class DummyBlob:
    def __init__(self, blob_id="b1"):
        self.id = blob_id
        self.blob = DummyBlobInner()


class DummyNote:
    def __init__(self, note_id="n1"):
        self.id = note_id
        self.title = "title"
        self.text = "text"
        self.pinned = False
        self.archived = False
        self.trashed = False
        self.type = type("T", (), {"value": "NOTE"})()
        self.color = type("C", (), {"value": "white"})()
        self.labels = DummyLabels()
        self.collaborators = DummyCollaborators()
        self.blobs = [DummyBlob()]
        self.deleted = False

    def delete(self):
        self.deleted = True

    def trash(self):
        self.trashed = True

    def untrash(self):
        self.trashed = False

    def undelete(self):
        self.deleted = False


class DummyKeep:
    def __init__(self):
        self.notes = {}
        self._labels = {"l1": DummyLabel("l1", "keep-agent-mem")}
        self.sync_calls = 0

    def sync(self):
        self.sync_calls += 1

    def find(self, **kwargs):
        self.last_find_kwargs = kwargs
        return list(self.notes.values())

    def get(self, note_id):
        return self.notes.get(note_id)

    def createNote(self, title=None, text=None):
        note = DummyNote("created")
        note.title = title
        note.text = text
        self.notes[note.id] = note
        return note

    def findLabel(self, name):
        for label in self._labels.values():
            if label.name == name:
                return label
        return None

    def createLabel(self, name):
        label = DummyLabel("new", name)
        self._labels[label.id] = label
        return label

    def labels(self):
        return list(self._labels.values())

    def getLabel(self, label_id):
        return self._labels.get(label_id)

    def all(self):
        return list(self.notes.values())


@pytest.fixture()
def keep(monkeypatch):
    keep = DummyKeep()
    keep.notes["n1"] = DummyNote("n1")
    keep.notes["n1"].labels.add(DummyLabel("l1", "keep-agent-mem"))

    monkeypatch.setattr(cli, "get_client", lambda: keep)
    monkeypatch.setattr(
        cli.gkeepapi.node,
        "ColorValue",
        lambda color: type("Color", (), {"value": color})(),
    )
    return keep


def test_list_notes_forwards_filters(keep):
    result = cli.list_notes(
        query="q",
        labels=["l1"],
        colors=["red"],
        pinned=True,
        archived=False,
        trashed=False,
    )
    assert keep.last_find_kwargs["query"] == "q"
    assert keep.last_find_kwargs["labels"] == ["l1"]
    assert [color.value for color in keep.last_find_kwargs["colors"]] == ["red"]
    assert isinstance(result, list)


def test_list_notes_without_colors_passes_none(keep):
    cli.list_notes(query="q")
    assert keep.last_find_kwargs["colors"] is None


def test_list_notes_invalid_color_raises(keep, monkeypatch):
    def bad_color(_):
        raise ValueError("bad")

    monkeypatch.setattr(cli.gkeepapi.node, "ColorValue", bad_color)
    with pytest.raises(ValueError, match="Invalid color 'invalid'"):
        cli.list_notes(colors=["invalid"])


def test_create_labels_and_sync(keep):
    data = cli.create(label="keep-agent-mem", title="t", text="body")
    assert data["id"] == "created"
    assert keep.sync_calls == 1


def test_create_creates_label_when_missing(keep):
    keep._labels = {}
    data = cli.create(label="my-custom-label", title="t", text="body")
    assert data["labels"][0]["name"] == "my-custom-label"


def test_update_updates_fields(keep):
    data = cli.update("n1", title="new", text="changed")
    assert data["title"] == "new"
    assert data["text"] == "changed"


def test_update_not_found_raises(keep):
    with pytest.raises(ValueError, match="not found"):
        cli.update("missing", title="x")


def test_delete(keep):
    data = cli.delete("n1")
    assert data["message"] == "Note n1 marked for deletion"
    assert keep.notes["n1"].deleted is True
    assert keep.sync_calls == 1


def test_delete_not_found_raises(keep):
    with pytest.raises(ValueError, match="not found"):
        cli.delete("missing")


def test_main_runs_stdio_transport(monkeypatch):
    captured = {}

    def fake_run(*args, **kwargs):
        captured["transport"] = kwargs.get("transport", "stdio")

    monkeypatch.setattr(cli.mcp, "run", fake_run)
    cli.main()
    assert captured["transport"] == "stdio"


@pytest.fixture
async def main_mcp_client(keep):
    async with Client(cli.mcp) as client:
        yield client


async def test_integration_list_tools(main_mcp_client):
    tools = await main_mcp_client.list_tools()
    tool_names = [tool.name for tool in tools]
    assert "list_notes" in tool_names
    assert "create" in tool_names
    assert "update" in tool_names
    assert "delete" in tool_names

    # Assert schemas are populated
    find_tool = next(t for t in tools if t.name == "list_notes")
    assert "query" in find_tool.inputSchema["properties"]
    assert "labels" in find_tool.inputSchema["properties"]
    assert "colors" in find_tool.inputSchema["properties"]


async def test_integration_create_note(main_mcp_client, keep):
    result = await main_mcp_client.call_tool(
        name="create",
        arguments={
            "label": "keep-agent-mem",
            "title": "Integration test note",
            "text": "Hello world from integration test",
        },
    )
    assert result.structured_content is not None
    assert result.structured_content["title"] == "Integration test note"
    assert result.structured_content["text"] == "Hello world from integration test"
    assert keep.sync_calls == 1
