from typing import Literal

import gkeepapi
from fastmcp import FastMCP

from .keep_api import get_client, serialize_note, text_hash

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


def _normalize_color(color: str | None):
    if color is None:
        return None

    return _normalize_colors([color])[0]


def _label_ids_for_names(keep, label_names: list[str] | None):
    if not label_names:
        return []

    label_ids = []
    missing = []
    for name in label_names:
        label = keep.findLabel(name)
        if label:
            label_ids.append(label.id)
        else:
            missing.append(name)

    if missing:
        raise ValueError(f"Label names not found: {', '.join(missing)}")

    return label_ids


def _get_or_create_label(keep, name: str):
    get_label = getattr(keep, "getLabel", None)
    keep_label = get_label(name) if get_label else None
    if not keep_label:
        keep_label = keep.findLabel(name)
    if not keep_label:
        keep_label = keep.createLabel(name)
    return keep_label


def _collect_label_names(
    label: str | None = None,
    labels: list[str] | None = None,
    label_names: list[str] | None = None,
):
    names = []
    for value in [label, *(labels or []), *(label_names or [])]:
        if value and value not in names:
            names.append(value)
    return names


def _note_has_label_names(note, label_names: list[str] | None):
    if not label_names:
        return True
    names = {label.name for label in note.labels.all()}
    return all(label_name in names for label_name in label_names)


def _note_sort_value(note, sort_by: str):
    if sort_by == "title":
        return (note.title or "").lower()
    if sort_by == "pinned":
        return bool(note.pinned)

    if sort_by == "created":
        value = getattr(note, "created", None) or getattr(note, "created_at", None)
    else:
        value = (
            getattr(note, "updated", None)
            or getattr(note, "updated_at", None)
            or getattr(note, "timestamps", None)
        )

    if value is None:
        return ""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _set_note_metadata(note, color=None, pinned=None, archived=None, trashed=None):
    if color is not None:
        note.color = color
    if pinned is not None:
        note.pinned = pinned
    if archived is not None:
        note.archived = archived
    if trashed is not None:
        note.trashed = trashed


def _find_duplicate(keep, title: str | None, label_names: list[str], dedupe_by: str):
    if dedupe_by == "none":
        return None
    if dedupe_by not in {"title", "title_and_label"}:
        raise ValueError("dedupe_by must be one of: none, title, title_and_label")
    if not title:
        return None

    for note in keep.find(query=title, archived=None, trashed=False):
        if title is not None and note.title != title:
            continue
        if dedupe_by == "title_and_label" and not _note_has_label_names(note, label_names):
            continue
        return note

    return None


def _apply_text(note, text: str | None, text_mode: str):
    if text is None:
        return
    if text_mode == "replace":
        note.text = text
    elif text_mode == "append":
        note.text = f"{note.text or ''}{text}"
    elif text_mode == "prepend":
        note.text = f"{text}{note.text or ''}"
    else:
        raise ValueError("text_mode must be one of: replace, append, prepend")


def _list_item_text(item) -> str:
    if isinstance(item, dict):
        return str(item.get("text", ""))
    return str(item)


def _list_item_checked(item):
    return item.get("checked") if isinstance(item, dict) else None


def _delete_call(note, names: tuple[str, ...]):
    for name in names:
        method = getattr(note, name, None)
        if method:
            method()
            return True
    return False


@mcp.tool(
    annotations={
        "title": "List Google Keep notes",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
    tags={"keep", "read", "memory"},
)
def list_notes(
    query: str = "",
    note_ids: list[str] | None = None,
    labels: list[str] | None = None,
    label_names: list[str] | None = None,
    colors: list[str] | None = None,
    pinned: bool | None = None,
    archived: bool | None = False,
    trashed: bool | None = False,
    detail_level: Literal["summary", "metadata", "full"] = "summary",
    limit: int = 50,
    offset: int = 0,
    sort_by: Literal["updated", "created", "title", "pinned"] = "updated",
    sort_order: Literal["asc", "desc"] = "desc",
) -> list[dict]:
    """Search, list, or directly read notes with context-efficient output.

    Args:
        query: The search term or query string to search for in notes.
        note_ids: Optional note IDs for direct lookup without adding a separate get-note tool.
        labels: A list of label IDs to filter the notes by.
        label_names: A list of label names to filter by.
        colors: A list of ColorValue strings to filter by (e.g. DEFAULT, RED, CERULEAN).
        pinned: Filter notes by pinned status. True for pinned, False for unpinned, None for both.
        archived: Filter notes by archived status. Defaults to False.
        trashed: Filter notes by trashed status. Defaults to False.
        detail_level: summary returns compact note data, metadata omits text, full includes full text/media.
        limit: Maximum number of notes to return. Defaults to 50.
        offset: Number of matching notes to skip before returning results.
        sort_by: Sort key for the result set.
        sort_order: Sort order, ascending or descending.
    """
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("offset must be greater than or equal to 0")

    keep = get_client()
    normalized_colors = _normalize_colors(colors)
    label_ids = list(labels or []) + _label_ids_for_names(keep, label_names)

    if note_ids:
        notes = [keep.get(note_id) for note_id in note_ids]
        notes = [note for note in notes if note is not None]
    else:
        notes = keep.find(
            query=query,
            labels=label_ids or None,
            colors=normalized_colors,
            pinned=pinned,
            archived=archived,
            trashed=trashed,
        )

    notes = [note for note in notes if _note_has_label_names(note, label_names)]
    reverse = sort_order == "desc"
    notes = sorted(notes, key=lambda note: _note_sort_value(note, sort_by), reverse=reverse)
    notes = notes[offset : offset + limit]

    notes_data = [serialize_note(note, detail_level=detail_level) for note in notes]
    return notes_data


@mcp.tool(
    annotations={
        "title": "Create Google Keep memory",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
    tags={"keep", "create", "memory"},
)
def create(
    label: str | None = None,
    title: str | None = None,
    text: str | None = None,
    labels: list[str] | None = None,
    label_names: list[str] | None = None,
    note_type: Literal["note", "list"] = "note",
    items: list[dict | str] | None = None,
    color: str | None = None,
    pinned: bool | None = None,
    archived: bool | None = None,
    dedupe_by: Literal["none", "title", "title_and_label"] = "none",
    if_exists: Literal["create", "update", "return_existing", "error"] = "create",
) -> dict:
    """Create a note or list note with labels, metadata, and optional dedupe behavior.

    Args:
        label: Backward-compatible single label name. If absent, agents should use the current project/repository name.
        title: The title of the note.
        text: The text content of the note.
        labels: Additional label names to apply.
        label_names: Additional label names to apply.
        note_type: Create a regular note or a checklist/list note.
        items: List-note items as strings or dictionaries containing text and checked.
        color: Optional ColorValue string (e.g. DEFAULT, RED, CERULEAN).
        pinned: Optional initial pinned state.
        archived: Optional initial archived state.
        dedupe_by: Existing-note lookup mode before creating.
        if_exists: What to do when dedupe finds an existing note.
    """
    keep = get_client()
    label_names = _collect_label_names(label, labels, label_names)
    duplicate = _find_duplicate(keep, title, label_names, dedupe_by)

    if duplicate and if_exists == "return_existing":
        return serialize_note(duplicate)
    if duplicate and if_exists == "error":
        raise ValueError(f"A matching note already exists: {duplicate.id}")

    if duplicate and if_exists == "update":
        note = duplicate
        if title is not None:
            note.title = title
        _apply_text(note, text, "replace")
    elif note_type == "list":
        create_list = getattr(keep, "createList", None)
        if not create_list:
            raise ValueError("This Google Keep client does not support list-note creation")
        note = create_list(title=title, items=[_list_item_text(item) for item in items or []])
        for index, item in enumerate(getattr(note, "items", [])):
            if index < len(items or []):
                checked = _list_item_checked((items or [])[index])
                if checked is not None:
                    item.checked = checked
    else:
        note = keep.createNote(title=title, text=text)

    _set_note_metadata(note, color=_normalize_color(color), pinned=pinned, archived=archived)

    for label_name in label_names:
        note.labels.add(_get_or_create_label(keep, label_name))
    keep.sync()

    return serialize_note(note)


@mcp.tool(
    annotations={
        "title": "Update Google Keep memory",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
    tags={"keep", "update", "memory"},
)
def update(
    note_id: str,
    title: str | None = None,
    text: str | None = None,
    text_mode: Literal["replace", "append", "prepend"] = "replace",
    labels_add: list[str] | None = None,
    labels_remove: list[str] | None = None,
    color: str | None = None,
    pinned: bool | None = None,
    archived: bool | None = None,
    trashed: bool | None = None,
    expected_text_hash: str | None = None,
) -> dict:
    """Update note content, labels, metadata, and optional optimistic text hash.

    Args:
        note_id: The ID of the note to update.
        title: The new title for the note, if specified.
        text: The new body text for the note, if specified.
        text_mode: Replace, append, or prepend the provided text.
        labels_add: Label names to add, creating missing labels.
        labels_remove: Label names to remove when present.
        color: Optional ColorValue string (e.g. DEFAULT, RED, CERULEAN).
        pinned: Optional pinned state.
        archived: Optional archived state.
        trashed: Optional trashed state.
        expected_text_hash: If set, update only when the current text hash matches.
    """
    keep, note = _get_note_or_raise(note_id)

    if expected_text_hash and text_hash(getattr(note, "text", None)) != expected_text_hash:
        raise ValueError("Current note text does not match expected_text_hash")

    if title is not None:
        note.title = title
    _apply_text(note, text, text_mode)
    _set_note_metadata(
        note, color=_normalize_color(color), pinned=pinned, archived=archived, trashed=trashed
    )

    for label_name in labels_add or []:
        note.labels.add(_get_or_create_label(keep, label_name))

    existing_labels = {}
    for label in note.labels.all():
        existing_labels[label.name] = label
        existing_labels[label.id] = label
    for label_name_or_id in labels_remove or []:
        label = existing_labels.get(label_name_or_id)
        if label:
            note.labels.remove(label)

    keep.sync()
    return serialize_note(note)


@mcp.tool(
    annotations={
        "title": "Delete or restore Google Keep memory",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    },
    tags={"keep", "delete", "memory"},
)
def delete(
    note_id: str,
    mode: Literal["trash", "delete", "restore"] = "trash",
    confirm: bool = False,
) -> dict:
    """Trash, permanently delete, or restore a note by ID.

    Args:
        note_id: The ID of the note to delete.
        mode: trash is the safe default; delete requires confirm=True; restore untrashes/undeletes where supported.
        confirm: Required for mode=delete.
    """
    keep, note = _get_note_or_raise(note_id)

    if mode == "delete":
        if not confirm:
            raise ValueError("Permanent delete requires confirm=True")
        note_data = serialize_note(note)
        note.delete()
    elif mode == "restore":
        restored = _delete_call(note, ("untrash", "undelete"))
        if not restored:
            note.trashed = False
        note_data = serialize_note(note)
    else:
        trashed = _delete_call(note, ("trash",))
        if not trashed:
            note.trashed = True
        note_data = serialize_note(note)

    keep.sync()
    return {"message": f"Note {note_id} {mode} completed", "note": note_data}


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
