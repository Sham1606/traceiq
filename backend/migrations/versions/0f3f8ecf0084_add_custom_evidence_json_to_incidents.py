"""add_custom_evidence_json_to_incidents

Revision ID: 0f3f8ecf0084
Revises: 7ad0cf9b3bf7
Create Date: 2026-10-08 20:57:31.565981

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f3f8ecf0084'
down_revision: Union[str, Sequence[str], None] = '7ad0cf9b3bf7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('incidents', sa.Column('custom_evidence_json', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('incidents', 'custom_evidence_json')
