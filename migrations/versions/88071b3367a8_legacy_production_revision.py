"""legacy production revision placeholder

Revision ID: 88071b3367a8
Revises:
Create Date: 2026-04-04

"""

from typing import Sequence, Union

revision: str = "88071b3367a8"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("legacy_prod",)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
