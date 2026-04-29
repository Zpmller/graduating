"""increase_ip_address_length

Revision ID: 0797e7f68bb4
Revises: 089408542547
Create Date: 2026-02-03 04:34:13.352079

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0797e7f68bb4'
down_revision = '089408542547'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 修改ip_address字段长度从45增加到512（支持RTSP URL等长地址）
    op.alter_column('devices', 'ip_address',
                    existing_type=sa.String(length=45),
                    type_=sa.String(length=512),
                    existing_nullable=True)


def downgrade() -> None:
    # 回滚：将ip_address字段长度从512改回45
    op.alter_column('devices', 'ip_address',
                    existing_type=sa.String(length=512),
                    type_=sa.String(length=45),
                    existing_nullable=True)
