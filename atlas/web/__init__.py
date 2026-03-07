"""ATLAS Web Dashboard.

FastAPI-based web interface with HTMX for real-time updates.
"""

from .app import create_app

__all__ = ["create_app"]
