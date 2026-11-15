import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.core.enums.record_status import RecordStatus

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser


class FAQ(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "faqs"

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    question: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )

    status: Mapped[RecordStatus] = mapped_column(
        Enum(
            RecordStatus,
            name="record_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        default=RecordStatus.DRAFT,
        server_default=text("'draft'"),
        nullable=False,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_faqs_created_by",
        ),
        nullable=True,
    )

    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_faqs_updated_by",
        ),
        nullable=True,
    )

    creator: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys=[created_by],
        lazy="raise",
    )

    updater: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys=[updated_by],
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "ix_faqs_status_category_order",
            "status",
            "category",
            "display_order",
            postgresql_where=text("status = 'published'"),
        ),
        Index(
            "ix_faqs_category_order",
            "category",
            "display_order",
        ),
        Index(
            "ix_faqs_created_by",
            "created_by",
            postgresql_where=text("created_by IS NOT NULL"),
        ),
        Index(
            "ix_faqs_updated_by",
            "updated_by",
            postgresql_where=text("updated_by IS NOT NULL"),
        ),
        CheckConstraint(
            "length(trim(category)) > 0",
            name="ck_faqs_category_not_blank",
        ),
        CheckConstraint(
            "length(trim(question)) > 0",
            name="ck_faqs_question_not_blank",
        ),
        CheckConstraint(
            "length(trim(answer)) > 0",
            name="ck_faqs_answer_not_blank",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="ck_faqs_display_order_non_negative",
        ),
    )

    @validates("category", "question", "answer")
    def _strip_required(self, _key: str, value: str) -> str:
        return value.strip()
