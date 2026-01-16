"""Azure Virtual Desktop Manager - Main package."""

__version__ = "0.1.0"
__author__ = "QA Test Team"

from .connection_manager import ConnectionManager
from .session_handler import SessionHandler
from .config import Config

__all__ = ["ConnectionManager", "SessionHandler", "Config"]