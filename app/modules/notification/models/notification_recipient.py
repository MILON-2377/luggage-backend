import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.notification.enums import NotificationDeliveryStatus

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser
    from app.modules.notification.models.notification import Notification


class NotificationRecipient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_recipients"

    notification_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "notifications.id",
            ondelete="CASCADE",
            name="fk_notification_recipients_notification_id",
        ),
        nullable=False,
    )

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="CASCADE",
            name="fk_notification_recipients_admin_user_id",
        ),
        nullable=False,
    )

    delivery_status: Mapped[NotificationDeliveryStatus] = mapped_column(
        Enum(
            NotificationDeliveryStatus,
            name="notification_delivery_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
            create_constraint=True,
            validate_strings=True,
        ),
        default=NotificationDeliveryStatus.PENDING,
        server_default=text("'pending'"),
        nullable=False,
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    notification: Mapped["Notification"] = relationship(
        "Notification",
        back_populates="recipients",
        lazy="raise",
    )

    admin_user: Mapped["AdminUser"] = relationship(
        "AdminUser",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_notification_recipients_notification_admin",
            "notification_id",
            "admin_user_id",
            unique=True,
        ),
        Index(
            "ix_notification_recipients_admin_created_at",
            "admin_user_id",
            text("created_at DESC"),
        ),
        Index(
            "ix_notification_recipients_admin_unread",
            "admin_user_id",
            text("created_at DESC"),
            postgresql_where=text("read_at IS NULL"),
        ),
        Index(
            "ix_notification_recipients_undelivered",
            "created_at",
            postgresql_where=text("delivery_status IN ('pending', 'failed')"),
        ),
        CheckConstraint(
            "(delivery_status = 'delivered') = (delivered_at IS NOT NULL)",
            name="ck_notification_recipients_delivered_at_matches_status",
        ),
        CheckConstraint(
            "(delivery_status = 'failed') = (failed_at IS NOT NULL)",
            name="ck_notification_recipients_failed_at_matches_status",
        ),
        CheckConstraint(
            "failure_reason IS NULL OR delivery_status = 'failed'",
            name="ck_notification_recipients_failure_reason_only_when_failed",
        ),
        CheckConstraint(
            "read_at IS NULL OR delivered_at IS NOT NULL",
            name="ck_notification_recipients_read_requires_delivered",
        ),
    )

    @validates("failure_reason")
    def _strip_optional(
        self,
        _key: str,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        return value.strip() or None
