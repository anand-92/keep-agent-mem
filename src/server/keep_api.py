import os
from hashlib import sha256

import gkeepapi
import requests
from dotenv import load_dotenv

_keep_client = None

def get_client():
    """
    Get or initialize the Google Keep client.
    This ensures we only authenticate once and reuse the client.
    
    Returns:
        gkeepapi.Keep: Authenticated Keep client
    """
    global _keep_client
    
    if _keep_client is not None:
        _keep_client.sync()
        return _keep_client
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials from environment variables
    email = os.getenv('GOOGLE_EMAIL')
    master_token = os.getenv('GOOGLE_MASTER_TOKEN')
    
    if not email or not master_token:
        raise ValueError("Missing Google Keep credentials. Please set GOOGLE_EMAIL and GOOGLE_MASTER_TOKEN environment variables.")
    
    # Initialize the Keep API
    keep = gkeepapi.Keep()
    
    # Authenticate
    try:
        keep.authenticate(email, master_token)
    except requests.exceptions.JSONDecodeError as exc:
        raise RuntimeError(
            "Google Keep API returned a non-JSON response during authentication. "
            "This usually means the unofficial Keep API (notes/v1) is inaccessible "
            "from this environment (HTTP 403/4xx). "
            "Check that your GOOGLE_MASTER_TOKEN is valid and that the Keep API "
            "is reachable from this network."
        ) from exc
    except gkeepapi.exception.LoginException as exc:
        raise RuntimeError(
            f"Google Keep login failed: {exc}. "
            "Verify that GOOGLE_EMAIL and GOOGLE_MASTER_TOKEN are correct."
        ) from exc
    
    # Store the client for reuse
    _keep_client = keep
    
    # Sync to pick up any external changes
    keep.sync()
    
    return keep

def serialize_label(label):
    return {'id': label.id, 'name': label.name}


def serialize_list_item(item):
    return {
        'id': item.id,
        'text': item.text,
        'checked': item.checked,
        'parent_item_id': item.parent_item.id if item.parent_item else None,
    }


def _get_value(value):
    return value.value if hasattr(value, 'value') else value


def _get_timestamp(note, names):
    for name in names:
        value = getattr(note, name, None)
        if value is not None:
            return value.isoformat() if hasattr(value, 'isoformat') else value
    return None


def _text_preview(text, length=160):
    if not text:
        return ''
    normalized = ' '.join(str(text).split())
    if len(normalized) <= length:
        return normalized
    return f'{normalized[: length - 1]}…'


def text_hash(text):
    return sha256((text or '').encode('utf-8')).hexdigest()


def serialize_collaborator(collaborator):
    if isinstance(collaborator, str):
        return collaborator

    email = getattr(collaborator, 'email', None)
    if email:
        return email


    return str(collaborator)


def serialize_note(note, detail_level='full'):
    """
    Serialize a Google Keep note into a dictionary.
    
    Args:
        note: A Google Keep note object
        
    Returns:
        dict: A dictionary containing the note's id, title, text, pinned status, color and labels
    """
    payload = {
        'id': note.id,
        'title': note.title,
        'type': _get_value(note.type),
        'pinned': note.pinned,
        'archived': note.archived,
        'trashed': note.trashed,
        'color': _get_value(note.color) if note.color else None,
        'labels': [serialize_label(label) for label in note.labels.all()],
        'text_preview': _text_preview(getattr(note, 'text', None)),
        'text_hash': text_hash(getattr(note, 'text', None)),
        'created_at': _get_timestamp(note, ('created', 'created_at', 'create_time')),
        'updated_at': _get_timestamp(note, ('updated', 'updated_at', 'edit_time', 'timestamps')),
    }

    if detail_level == 'metadata':
        return payload

    payload['text'] = note.text

    if detail_level == 'summary':
        return payload

    payload['collaborators'] = [serialize_collaborator(collaborator) for collaborator in note.collaborators.all()]

    if hasattr(note, 'items'):
        payload['items'] = [serialize_list_item(item) for item in note.items]

    payload['media'] = [
        {
            'blob_id': blob.id,
            'type': _get_value(blob.blob.type) if blob.blob and blob.blob.type else None,
        }
        for blob in note.blobs
    ]

    return payload
