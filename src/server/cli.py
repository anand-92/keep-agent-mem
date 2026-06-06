import gkeepapi
from fastmcp import FastMCP

from .keep_api import get_client, serialize_note

mcp = FastMCP("keep")


def _get_note_or_raise(note_id: str):
    keep = get_client()
    note = keep.get(note_id)
    if not note:
        raise ValueError(f"Note with ID {note_id} not found")
    return keep, note


def _normalize_colors(colors: list[str] | None):
    if colors is None:
        return None

    normalized_colors = []
    for color in colors:
        try:
            normalized_colors.append(gkeepapi.node.ColorValue(color))
        except ValueError as exc:
            raise ValueError(f"Invalid color '{color}'") from exc

    return normalized_colors


@mcp.tool()
def list_notes(
    query: str = "",
    labels: list[str] | None = None,
    colors: list[str] | None = None,
    pinned: bool | None = None,
    archived: bool | None = False,
    trashed: bool = False,
) -> list[dict]:
    """List all notes with optional filters.

    Args:
        query: The search term or query string to search for in notes.
        labels: A list of label IDs to filter the notes by.
        colors: A list of ColorValue strings to filter by (e.g. DEFAULT, RED, CERULEAN).
        pinned: Filter notes by pinned status. True for pinned, False for unpinned, None for both.
        archived: Filter notes by archived status. Defaults to False.
        trashed: Filter notes by trashed status. Defaults to False.
    """
    keep = get_client()
    normalized_colors = _normalize_colors(colors)
    notes = keep.find(
        query=query,
        labels=labels,
        colors=normalized_colors,
        pinned=pinned,
        archived=archived,
        trashed=trashed,
    )

    notes_data = [serialize_note(note) for note in notes]
    return notes_data


@mcp.tool()
def create(label: str, title: str | None = None, text: str | None = None) -> dict:
    """Create a new note with a title, text, and an associated label.

    Args:
        label: The label to apply to the note. If the user does not explicitly specify a label, the client (e.g. LLM agent) MUST use the name of the current project or repository as the label.
        title: The title of the note.
        text: The text content of the note.
    """
    keep = get_client()
    note = keep.createNote(title=title, text=text)

    keep_label = keep.findLabel(label)
    if not keep_label:
        keep_label = keep.createLabel(label)

    note.labels.add(keep_label)
    keep.sync()

    return serialize_note(note)


@mcp.tool()
def update(note_id: str, title: str | None = None, text: str | None = None) -> dict:
    """Update a note's properties.

    Args:
        note_id: The ID of the note to update.
        title: The new title for the note, if specified.
        text: The new body text for the note, if specified.
    """
    keep, note = _get_note_or_raise(note_id)

    if title is not None:
        note.title = title
    if text is not None:
        note.text = text

    keep.sync()
    return serialize_note(note)


@mcp.tool()
def delete(note_id: str) -> dict:
    """Delete a note by ID.

    Args:
        note_id: The ID of the note to delete.
    """
    keep, note = _get_note_or_raise(note_id)
    note.delete()
    keep.sync()
    return {"message": f"Note {note_id} marked for deletion"}


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
