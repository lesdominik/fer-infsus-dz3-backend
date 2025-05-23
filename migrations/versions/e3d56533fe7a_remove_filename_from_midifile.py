"""Remove filename from MidiFile

Revision ID: e3d56533fe7a
Revises: 0ba9d97fad89
Create Date: 2025-05-23 16:25:27.030447

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3d56533fe7a'
down_revision = '0ba9d97fad89'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('midi_file', schema=None) as batch_op:
        batch_op.drop_column('filename')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('midi_file', schema=None) as batch_op:
        batch_op.add_column(sa.Column('filename', sa.VARCHAR(length=255), autoincrement=False, nullable=False))

    # ### end Alembic commands ###
