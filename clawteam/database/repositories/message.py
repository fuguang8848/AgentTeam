"""Message repository."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseRepository
from ..types import DatabaseMessage


class MessageRepository(BaseRepository[DatabaseMessage]):
    """Message repository."""

    def _table_name(self) -> str:
        return "messages"

    def _id_field(self) -> str:
        return "id"

    def _to_model(self, row: Dict[str, Any]) -> DatabaseMessage:
        """Convert database row to DatabaseMessage."""
        # Parse datetimes
        created_at = self._parse_datetime(row.get("created_at"))
        expires_at = self._parse_datetime(row.get("expires_at"))

        # Parse boolean
        delivered = bool(row.get("delivered", 0))

        return DatabaseMessage(
            id=row["id"],
            sender=row["sender"],
            recipient=row["recipient"],
            content=row["content"],
            team_id=row.get("team_id"),
            task_id=row.get("task_id"),
            session_id=row.get("session_id"),
            created_at=created_at or datetime.now(),
            expires_at=expires_at,
            delivered=delivered,
        )

    def _from_model(self, model: DatabaseMessage) -> Dict[str, Any]:
        """Convert DatabaseMessage to database row."""
        return {
            "id": model.id,
            "sender": model.sender,
            "recipient": model.recipient,
            "content": model.content,
            "team_id": model.team_id,
            "task_id": model.task_id,
            "session_id": model.session_id,
            "created_at": self._serialize_datetime(model.created_at),
            "expires_at": self._serialize_datetime(model.expires_at),
            "delivered": 1 if model.delivered else 0,
        }

    def list(
        self,
        recipient: Optional[str] = None,
        team_id: Optional[str] = None,
        delivered: Optional[bool] = None,
        limit: int = 100,
    ) -> List[DatabaseMessage]:
        """Get messages with optional filters."""
        filters = {}
        if recipient is not None:
            filters["recipient"] = recipient
        if team_id is not None:
            filters["team_id"] = team_id
        if delivered is not None:
            filters["delivered"] = delivered

        messages = super().list(**filters)
        return messages[:limit]

    def mark_as_delivered(self, message_id: str) -> bool:
        """Mark message as delivered."""
        updates = {"delivered": 1}
        result = self.update(message_id, updates)
        return result is not None

    def mark_batch_as_delivered(self, message_ids: List[str]) -> int:
        """Mark multiple messages as delivered."""
        count = 0
        for msg_id in message_ids:
            if self.mark_as_delivered(msg_id):
                count += 1
        return count

    def get_undelivered_messages(self, recipient: str) -> List[DatabaseMessage]:
        """Get undelivered messages for a recipient."""
        filters = {
            "recipient": recipient,
            "delivered": False,
        }
        return super().list(**filters)

    def cleanup_expired(self) -> int:
        """Delete expired messages."""
        if self.using_sqlite and self.db:
            # Delete messages where expires_at < current time
            query = "DELETE FROM messages WHERE expires_at IS NOT NULL AND expires_at < ?"
            cursor = self.db.execute(query, (datetime.now().isoformat(),))
            deleted = cursor.rowcount
            self.db.commit()

            # Also clean up memory storage
            expired_ids = []
            for msg_id, msg in self.mem_storage.items():
                if msg.expires_at and msg.expires_at < datetime.now():
                    expired_ids.append(msg_id)

            for msg_id in expired_ids:
                del self.mem_storage[msg_id]

            return max(deleted, len(expired_ids))
        else:
            # Clean up memory storage
            expired_ids = []
            for msg_id, msg in self.mem_storage.items():
                if msg.expires_at and msg.expires_at < datetime.now():
                    expired_ids.append(msg_id)

            for msg_id in expired_ids:
                del self.mem_storage[msg_id]

            return len(expired_ids)

    def get_message_count_by_recipient(self) -> Dict[str, int]:
        """Get message count by recipient."""
        if self.using_sqlite and self.db:
            query = "SELECT recipient, COUNT(*) as count FROM messages GROUP BY recipient"
            cursor = self.db.execute(query)
            result = {}
            for row in cursor.fetchall():
                result[row["recipient"]] = row["count"]
            return result
        else:
            # Count in memory
            result = {}
            for msg in self.mem_storage.values():
                result[msg.recipient] = result.get(msg.recipient, 0) + 1
            return result
