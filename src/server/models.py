"""Typed output models for keep-agent-mem MCP tools.

These Pydantic models replace loose ``dict`` / ``list[dict]`` return contracts so
FastMCP can publish precise JSON-Schema output descriptors to MCP clients and LLM agents.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LabelModel(BaseModel):
    """A Google Keep label."""

    id: str = Field(..., description="Unique label ID.")
    name: str = Field(..., description="Human-readable label name.")


class ListItemModel(BaseModel):
    """A single checklist item inside a list-type note."""

    id: str = Field(..., description="Unique item ID.")
    text: str = Field(..., description="Item text.")
    checked: bool = Field(..., description="Whether the item is checked/completed.")
    parent_item_id: str | None = Field(None, description="Parent item ID for nested items.")


class MediaModel(BaseModel):
    """A media blob attached to a note."""

    blob_id: str = Field(..., description="Unique blob ID.")
    type: str | None = Field(None, description="Blob media type (e.g. IMAGE).")


class NoteModel(BaseModel):
    """A serialized Google Keep note.

    Fields present depend on the ``detail_level`` used when fetching:
    - ``metadata``: id through updated_at only (no text).
    - ``summary``: adds ``text`` field.
    - ``full``: adds collaborators, items, and media.
    """

    id: str = Field(..., description="Unique note ID.")
    title: str | None = Field(None, description="Note title.")
    type: str = Field(..., description="Note type: NOTE or LIST.")
    pinned: bool = Field(..., description="Whether the note is pinned.")
    archived: bool = Field(..., description="Whether the note is archived.")
    trashed: bool = Field(..., description="Whether the note is trashed.")
    color: str | None = Field(None, description="Note color value (e.g. DEFAULT, RED).")
    labels: list[LabelModel] = Field(
        default_factory=list, description="Labels attached to this note."
    )
    text_preview: str = Field("", description="Truncated plain-text preview (up to 160 chars).")
    text_hash: str = Field(
        ..., description="SHA-256 hash of the full note text for optimistic locking."
    )
    created_at: str | None = Field(None, description="ISO-8601 creation timestamp.")
    updated_at: str | None = Field(None, description="ISO-8601 last-updated timestamp.")
    # summary / full fields
    text: str | None = Field(
        None, description="Full note text (present for summary and full detail levels)."
    )
    # full-only fields
    collaborators: list[str] | None = Field(
        None, description="Collaborator email addresses (present for full detail level)."
    )
    items: list[ListItemModel] | None = Field(
        None, description="Checklist items for list-type notes (present for full detail level)."
    )
    media: list[MediaModel] | None = Field(
        None, description="Attached media blobs (present for full detail level)."
    )

    model_config = {"extra": "allow"}

    @classmethod
    def from_dict(cls, data: dict) -> "NoteModel":
        """Build a NoteModel from the plain dict produced by serialize_note()."""
        labels = [LabelModel(**lbl) for lbl in data.get("labels", [])]
        items = (
            [ListItemModel(**item) for item in data["items"]]
            if data.get("items") is not None
            else None
        )
        media = [MediaModel(**m) for m in data["media"]] if data.get("media") is not None else None
        collaborators = data.get("collaborators")
        return cls(
            id=data["id"],
            title=data.get("title"),
            type=data["type"],
            pinned=data["pinned"],
            archived=data["archived"],
            trashed=data["trashed"],
            color=data.get("color"),
            labels=labels,
            text_preview=data.get("text_preview", ""),
            text_hash=data["text_hash"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            text=data.get("text"),
            collaborators=collaborators,
            items=items,
            media=media,
        )


class DeleteResponse(BaseModel):
    """Response returned by the ``delete`` tool."""

    message: str = Field(..., description="Human-readable status message.")
    note: NoteModel = Field(..., description="Snapshot of the note before/after the operation.")


# ---------------------------------------------------------------------------
# Tool meta constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"
BACKEND = "google_keep"

LIST_NOTES_META: dict = {
    "schema_version": SCHEMA_VERSION,
    "backend": BACKEND,
    "compatibility": "Backward-compatible with keep-agent-mem <=0.3.0",
    "preferred_params": ["query", "label_names", "detail_level", "limit", "offset"],
}

CREATE_META: dict = {
    "schema_version": SCHEMA_VERSION,
    "backend": BACKEND,
    "compatibility": "Backward-compatible with keep-agent-mem <=0.3.0",
    "preferred_params": ["label", "title", "text", "note_type"],
    "deprecations": {
        "labels": "Prefer 'label' or 'label_names' for clarity.",
    },
}

UPDATE_META: dict = {
    "schema_version": SCHEMA_VERSION,
    "backend": BACKEND,
    "compatibility": "Backward-compatible with keep-agent-mem <=0.3.0",
    "preferred_params": ["note_id", "text", "text_mode", "expected_text_hash"],
}

DELETE_META: dict = {
    "schema_version": SCHEMA_VERSION,
    "backend": BACKEND,
    "compatibility": "Backward-compatible with keep-agent-mem <=0.3.0",
    "preferred_params": ["note_id", "mode"],
    "notes": "Default mode='trash' is safe and reversible. Use mode='delete' with confirm=True for permanent removal.",
}


# ---------------------------------------------------------------------------
# Parameter type aliases with Field metadata (used via Annotated in cli.py)
# ---------------------------------------------------------------------------

LimitField = Field(50, ge=1, le=200, description="Maximum number of notes to return (1–200).")
OffsetField = Field(
    0, ge=0, description="Number of matching notes to skip before returning results."
)
TitleField = Field(None, description="Note title.")
TextBodyField = Field(None, description="Note body text.")
ColorField = Field(
    None,
    description=(
        "Optional ColorValue string. "
        "Accepted values: DEFAULT, WHITE, RED, PINK, YELLOW, BLUE, GRAY, TEAL, GREEN, "
        "CERULEAN, PURPLE, ORANGE."
    ),
)
ExpectedTextHashField = Field(
    None,
    description=(
        "SHA-256 hash of the current note text for optimistic concurrency control. "
        "If set, the update is applied only when the stored hash matches."
    ),
)

# Literal type aliases kept as plain type aliases (used directly in signatures)
DetailLevelType = Literal["summary", "metadata", "full"]
SortByType = Literal["updated", "created", "title", "pinned"]
SortOrderType = Literal["asc", "desc"]
NoteTypeType = Literal["note", "list"]
DedupeByType = Literal["none", "title", "title_and_label"]
IfExistsType = Literal["create", "update", "return_existing", "error"]
TextModeType = Literal["replace", "append", "prepend"]
DeleteModeType = Literal["trash", "delete", "restore"]
