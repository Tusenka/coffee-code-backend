import logging
from datetime import datetime, UTC
from typing import List, Any
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from db.engineer import DbEngine
from db.enums import NotificationType
from db.model import Notification

logger = logging.getLogger(__name__)


class NotificationRepository:
    def __init__(self):
        self.db = DbEngine()

    def create(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        title: str | None = None,
        message: str | None = None,
        match_id: UUID | None = None,
        request_id: UUID | None = None,
    ) -> Notification:
        """Create a new notification."""

        with self.db.get_session() as session:
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                title=title,
                message=message,
                match_id=match_id,
                request_id=request_id,
            )
            session.add(notification)

            return notification

    def get_notification_by_id(self, notification_id: UUID) -> Notification | None:
        """Retrieve a notification by its ID."""
        with self.db.get_session() as session:
            result = self._get_notification_by_id(notification_id, session)

            return result

    @staticmethod
    def _get_notification_by_id(notification_id: UUID, session: Session) -> Any | None:
        stmt = select(Notification).where(Notification.id == notification_id)
        result = session.execute(stmt).unique().one_or_none()

        return result[0] if result else None

    def list_notifications(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> List[Notification]:
        """List notifications for a user, optionally only unread."""
        with self.db.get_session() as session:
            stmt = select(Notification).where(Notification.user_id == user_id)

            if unread_only:
                stmt = stmt.where(Notification.read_at.is_(None))
            stmt = (
                stmt.order_by(desc(Notification.created_at)).limit(limit).offset(offset)
            )
            result = session.execute(stmt).unique().all()

            return [row[0] for row in result]

    def mark_as_read(self, notification_id: UUID):
        """Mark a notification as read (set read_at to current timestamp)."""
        with self.db.get_session() as session:
            notification = self._get_notification_by_id(
                notification_id, session=session
            )

            if notification and not notification.read_at:
                notification.read_at = datetime.now(UTC)

    def mark_all_as_read(self, user_id: UUID, session: Session | None = None) -> int:
        """Mark all unread notifications for a user as read."""
        with self.db.get_session() as session:
            stmt = select(Notification).where(
                Notification.user_id == user_id, Notification.read_at.is_(None)
            )
            notifications = session.execute(stmt).scalars().all()

            for n in notifications:
                n.read_at = datetime.now(UTC)

            return len(notifications)

    def delete(self, notification_id: UUID) -> None:
        """Delete a notification."""
        with self.db.get_session() as session:
            notification = self._get_notification_by_id(
                notification_id, session=session
            )

            if notification:
                session.delete(notification)

    def count_unread(self, user_id: UUID) -> int:
        """Count unread notifications for a user."""
        with self.db.get_session() as session:
            return (
                session.query(Notification)
                .where(Notification.user_id == user_id, Notification.read_at.is_(None))
                .count()
            )
