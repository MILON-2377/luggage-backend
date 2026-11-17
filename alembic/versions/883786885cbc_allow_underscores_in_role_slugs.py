"""allow underscores in role slugs

Revision ID: 883786885cbc
Revises: b1533c594967
Create Date: 2026-11-17 19:40:28.026471

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '883786885cbc'
down_revision: Union[str, Sequence[str], None] = 'b1533c594967'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.drop_constraint(
        "ck_roles_slug_format",
        "roles",
        type_="check",
    )

    op.create_check_constraint(
        "ck_roles_slug_format",
        "roles",
        "slug = lower(slug) AND slug ~ '^[a-z0-9]+([-_][a-z0-9]+)*$'",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_roles_slug_format",
        "roles",
        type_="check",
    )

    op.create_check_constraint(
        "ck_roles_slug_format",
        "roles",
        "slug = lower(slug) AND slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
    )

