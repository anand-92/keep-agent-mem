import gkeepapi
import os
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


def serialize_note(note):
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
        'text': note.text,
        'type': note.type.value,
        'pinned': note.pinned,
        'archived': note.archived,
        'trashed': note.trashed,
        'color': note.color.value if note.color else None,
        'labels': [serialize_label(label) for label in note.labels.all()],
        'collaborators': list(note.collaborators.all()),
    }

    if hasattr(note, 'items'):
        payload['items'] = [serialize_list_item(item) for item in note.items]

    payload['media'] = [
        {
            'blob_id': blob.id,
            'type': blob.blob.type.value if blob.blob and blob.blob.type else None,
        }
        for blob in note.blobs
    ]

    return payload
