"""Session management for conversation history."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions with file-based storage."""

    def __init__(self, storage_path: str = "./sessions"):
        """Initialize session manager.

        Args:
            storage_path: Directory to store session files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info("Session manager initialized with storage at %s", self.storage_path)

    def _get_session_file(self, user_id: str) -> Path:
        """Get the file path for a user's session.

        Args:
            user_id: User identifier

        Returns:
            Path to the session file
        """
        # Sanitize user_id to be filesystem-safe
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("_", "-"))
        return self.storage_path / f"{safe_user_id}.json"

    def load_session(self, user_id: str) -> dict[str, Any] | None:
        """Load a user's session from disk.

        Args:
            user_id: User identifier

        Returns:
            Session data dictionary or None if not found
        """
        session_file = self._get_session_file(user_id)

        if not session_file.exists():
            logger.debug("No existing session for user %s", user_id)
            return None

        try:
            with session_file.open() as f:
                session_data: dict[str, Any] = json.load(f)
            logger.debug("Loaded session for user %s", user_id)
            return session_data
        except Exception as e:
            logger.error("Error loading session for user %s: %s", user_id, e)
            return None

    def save_session(self, user_id: str, session_data: dict[str, Any]) -> bool:
        """Save a user's session to disk.

        Args:
            user_id: User identifier
            session_data: Session data to save

        Returns:
            True if successful, False otherwise
        """
        session_file = self._get_session_file(user_id)

        try:
            with session_file.open("w") as f:
                json.dump(session_data, f, indent=2)
            logger.debug("Saved session for user %s", user_id)
            return True
        except Exception as e:
            logger.error("Error saving session for user %s: %s", user_id, e)
            return False

    def create_session(self, user_id: str) -> dict[str, Any]:
        """Create a new session for a user.

        Args:
            user_id: User identifier

        Returns:
            New session data dictionary
        """
        session_data = {
            "user_id": user_id,
            "messages": [],
            "config": {},
        }
        self.save_session(user_id, session_data)
        logger.info("Created new session for user %s", user_id)
        return session_data

    def get_or_create_session(self, user_id: str) -> dict[str, Any]:
        """Get an existing session or create a new one.

        Args:
            user_id: User identifier

        Returns:
            Session data dictionary
        """
        session = self.load_session(user_id)
        if session is None:
            session = self.create_session(user_id)
        return session

    def add_message(self, user_id: str, role: str, content: str) -> dict[str, Any]:
        """Add a message to the user's session.

        Args:
            user_id: User identifier
            role: Message role (user, assistant, system)
            content: Message content

        Returns:
            Updated session data
        """
        session = self.get_or_create_session(user_id)

        message = {"role": role, "content": content}
        session["messages"].append(message)

        self.save_session(user_id, session)
        return session

    def get_messages(self, user_id: str) -> list[dict[str, str]]:
        """Get all messages for a user.

        Args:
            user_id: User identifier

        Returns:
            List of messages
        """
        session = self.get_or_create_session(user_id)
        messages: list[dict[str, str]] = session.get("messages", [])
        return messages

    def clear_session(self, user_id: str) -> bool:
        """Clear a user's session.

        Args:
            user_id: User identifier

        Returns:
            True if successful
        """
        session_file = self._get_session_file(user_id)

        try:
            if session_file.exists():
                session_file.unlink()
                logger.info("Cleared session for user %s", user_id)
            return True
        except Exception as e:
            logger.error("Error clearing session for user %s: %s", user_id, e)
            return False
