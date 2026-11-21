"""add pending mfa setup status

Revision ID: a3876402d281
Revises: 0f48950669aa
Create Date: 2026-11-18 16:50:55.884446

"""

from typing import Sequence, Union

from alembic import op

revision: str = "a3876402d281"
down_revision: Union[str, Sequence[str], None] = "0f48950669aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "admin_user_status",
        "admin_users",
        type_="check",
    )

    op.create_check_constraint(
        "admin_user_status",
        "admin_users",
        """
        status IN (
            'invited',
            'pending_mfa_setup',
            'active',
            'disabled',
            'suspended'
        )
        """,
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE admin_users
        SET status = 'disabled'
        WHERE status = 'pending_mfa_setup'
        """
    )

    op.drop_constraint(
        "admin_user_status",
        "admin_users",
        type_="check",
    )

    op.create_check_constraint(
        "admin_user_status",
        "admin_users",
        """
        status IN (
            'invited',
            'active',
            'disabled',
            'suspended'
        )
        """,
    )