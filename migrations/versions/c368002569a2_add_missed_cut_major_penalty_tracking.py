"""add missed-cut major penalty tracking

Revision ID: c368002569a2
Revises: 79cce13ad2fb
Create Date: 2026-04-11 17:46:52.189131

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c368002569a2'
down_revision = '79cce13ad2fb'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('pick', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'penalty_triggered',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('0'),
        ))

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'penalty_paid',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
        ))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('penalty_paid')

    with op.batch_alter_table('pick', schema=None) as batch_op:
        batch_op.drop_column('penalty_triggered')
