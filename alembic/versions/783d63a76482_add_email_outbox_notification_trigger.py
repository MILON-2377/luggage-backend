"""add email outbox notification trigger

Revision ID: 783d63a76482
Revises: 53d384c31aab
Create Date: 2026-11-19 22:54:09.712663

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '783d63a76482'
down_revision: Union[str, Sequence[str], None] = '53d384c31aab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION notify_email_outbox_insert()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            PERFORM pg_notify(
                'email_outbox_wakeup',
                NEW.id::text
            );

            RETURN NEW;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_email_outbox_insert_notification
        AFTER INSERT ON email_outbox
        FOR EACH ROW
        EXECUTE FUNCTION notify_email_outbox_insert();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_email_outbox_insert_notification
        ON email_outbox;
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS notify_email_outbox_insert();
        """
    )