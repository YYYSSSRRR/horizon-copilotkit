"""Utility functions."""

import uuid


def random_id() -> str:
    """Generate a random ID."""
    return str(uuid.uuid4())