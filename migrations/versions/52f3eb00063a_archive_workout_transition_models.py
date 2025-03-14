"""archive workout transition models

Revision ID: 52f3eb00063a
Revises: 8edab4b5fa9e
Create Date: 2025-03-10 15:13:52.477046

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '52f3eb00063a'
down_revision = '8edab4b5fa9e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('playlist_archive',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('original_spotify_id', sa.String(length=100), nullable=False),
    sa.Column('archive_spotify_id', sa.String(length=100), nullable=False),
    sa.Column('archived_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('workout_profile',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('workout_type', sa.String(length=50), nullable=False),
    sa.Column('target_bpm', sa.Integer(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('playlist_transition',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('playlist_id', sa.Integer(), nullable=False),
    sa.Column('from_track', sa.String(length=100), nullable=False),
    sa.Column('to_track', sa.String(length=100), nullable=False),
    sa.Column('transition_type', sa.String(length=50), nullable=False),
    sa.Column('duration', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['playlist_id'], ['playlist.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('playlist_transition')
    op.drop_table('workout_profile')
    op.drop_table('playlist_archive')
    # ### end Alembic commands ###
