"""add last_reminder_type to Tournament

Revision ID: 79cce13ad2fb
Revises: 7f95f6308352
Create Date: 2026-03-18 09:42:04.812359

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '79cce13ad2fb'
down_revision = '7f95f6308352'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('tournament', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_reminder_type', sa.String(length=10), nullable=True))


def downgrade():
    with op.batch_alter_table('tournament', schema=None) as batch_op:
        batch_op.drop_column('last_reminder_type')
