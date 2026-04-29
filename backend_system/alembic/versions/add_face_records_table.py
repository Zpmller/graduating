"""add face_records table

Revision ID: add_face_records
Revises: 089408542547
Create Date: 2026-03-01

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_face_records'
down_revision = '0797e7f68bb4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'face_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('person_name', sa.String(length=100), nullable=False),
        sa.Column('file_path', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_face_records_id'), 'face_records', ['id'], unique=False)
    op.create_index(op.f('ix_face_records_person_name'), 'face_records', ['person_name'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_face_records_person_name'), table_name='face_records')
    op.drop_index(op.f('ix_face_records_id'), table_name='face_records')
    op.drop_table('face_records')
