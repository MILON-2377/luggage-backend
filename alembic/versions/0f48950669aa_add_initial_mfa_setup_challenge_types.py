"""add initial mfa setup challenge types

Revision ID: 0f48950669aa
Revises: 883786885cbc
Create Date: 2026-11-18 16:14:56.384443

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0f48950669aa"
down_revision: Union[str, Sequence[str], None] = "883786885cbc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "challenge_type",
        "auth_challenges",
        type_="check",
    )

    op.create_check_constraint(
        "challenge_type",
        "auth_challenges",
        """
        challenge_type IN (
            'email_verification',
            'password_reset',
            'mfa_authentication',
            'totp_enrollment',
            'webauthn_registration',
            'account_recovery',
            'initial_mfa_setup',
            'mfa_enrollment_session'
        )
        """,
    )


def downgrade() -> None:
    op.drop_constraint(
        "challenge_type",
        "auth_challenges",
        type_="check",
    )

    op.create_check_constraint(
        "challenge_type",
        "auth_challenges",
        """
        challenge_type IN (
            'email_verification',
            'password_reset',
            'mfa_authentication',
            'totp_enrollment',
            'webauthn_registration',
            'account_recovery'
        )
        """,
    )
