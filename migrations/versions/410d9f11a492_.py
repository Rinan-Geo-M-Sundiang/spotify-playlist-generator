"""empty message

Revision ID: 410d9f11a492
Revises: 7b860cdb1023
Create Date: 2025-03-08 22:12:42.235346

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '410d9f11a492'
down_revision = '7b860cdb1023'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('favorite',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('spotify_id', sa.String(length=200), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_rating',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('spotify_track_id', sa.String(length=200), nullable=False),
    sa.Column('rating', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.add_column(sa.Column('spotify_track_id', sa.String(length=200), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.drop_column('spotify_track_id')

    op.drop_table('user_rating')
    op.drop_table('favorite')
    # ### end Alembic commands ###
