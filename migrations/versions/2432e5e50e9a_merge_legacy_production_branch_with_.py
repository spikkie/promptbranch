"""merge legacy production branch with current head

Revision ID: 2432e5e50e9a
Revises: 40a0941d87e9, 06765d196f0e
Create Date: 2026-04-05 10:36:22.724102

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2432e5e50e9a'
down_revision: Union[str, None] = ('40a0941d87e9', '06765d196f0e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
