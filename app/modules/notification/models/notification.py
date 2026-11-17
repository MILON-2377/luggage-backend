import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.notification.enums import (
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser
    from app.modules.notification.models.notification_recipient import (
        NotificationRecipient,
    )


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(
            NotificationType,
            name="notification_type",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=50,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )

    resource_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )

    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(
            NotificationChannel,
            name="notification_channel",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
            create_constraint=True,
            validate_strings=True,
        ),
        default=NotificationChannel.IN_APP,
        server_default=text("'in_app'"),
        nullable=False,
    )

    priority: Mapped[NotificationPriority] = mapped_column(
        Enum(
            NotificationPriority,
            name="notification_priority",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        default=NotificationPriority.NORMAL,
        server_default=text("'normal'"),
        nullable=False,
    )

    status: Mapped[NotificationStatus] = mapped_column(
        Enum(
            NotificationStatus,
            name="notification_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        default=NotificationStatus.PENDING,
        server_default=text("'pending'"),
        nullable=False,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_notifications_created_by",
        ),
        nullable=True,
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    creator: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys=[created_by],
        lazy="raise",
    )

    recipients: Mapped[list["NotificationRecipient"]] = relationship(
        "NotificationRecipient",
        back_populates="notification",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "ix_notifications_dispatch_queue",
            "scheduled_at",
            "created_at",
            postgresql_where=text("status IN ('pending', 'scheduled')"),
        ),
        Index(
            "ix_notifications_resource",
            "resource_type",
            "resource_id",
            postgresql_where=text("resource_id IS NOT NULL"),
        ),
        Index(
            "ix_notifications_type_status_created_at",
            "notification_type",
            "status",
            text("created_at DESC"),
        ),
        Index(
            "ix_notifications_created_by",
            "created_by",
            postgresql_where=text("created_by IS NOT NULL"),
        ),
        CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_notifications_title_not_blank",
        ),
        CheckConstraint(
            "length(trim(message)) > 0",
            name="ck_notifications_message_not_blank",
        ),
        CheckConstraint(
            "(resource_type IS NULL) = (resource_id IS NULL)",
            name="ck_notifications_resource_together",
        ),
        CheckConstraint(
            "(status = 'sent') = (sent_at IS NOT NULL)",
            name="ck_notifications_sent_at_matches_status",
        ),
        CheckConstraint(
            "status != 'scheduled' OR scheduled_at IS NOT NULL",
            name="ck_notifications_scheduled_at_required",
        ),
    )

    @validates("title", "message")
    def _strip_required(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("resource_type")
    def _normalize_resource_type(
        self,
        _key: str,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        return value.strip().lower() or None