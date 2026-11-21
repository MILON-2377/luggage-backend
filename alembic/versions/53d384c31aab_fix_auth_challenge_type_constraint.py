"""fix auth challenge type constraint

Revision ID: 53d384c31aab
Revises: a3876402d281
Create Date: 2026-11-18 21:47:11.973877

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "53d384c31aab"
down_revision: Union[str, Sequence[str], None] = "a3876402d281"
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
    op.execute(
        """
        DELETE FROM auth_challenges
        WHERE challenge_type IN (
            'initial_mfa_setup',
            'mfa_enrollment_session'
        )
        """
    )

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
