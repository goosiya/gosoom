"""add_quotes_table

Revision ID: d7bffeb07473
Revises: fc7ff3f42acd
Create Date: 2026-06-09 20:43:25.175782

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7bffeb07473'
down_revision: Union[str, Sequence[str], None] = 'fc7ff3f42acd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('quotes',
    sa.Column('service_request_id', sa.UUID(), nullable=False),
    sa.Column('pro_id', sa.UUID(), nullable=False),
    sa.Column('price', sa.Integer(), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'accepted', 'rejected', 'closed', name='quote_status'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['pro_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['service_request_id'], ['service_requests.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_quotes_pro_id'), 'quotes', ['pro_id'], unique=False)
    op.create_index(op.f('ix_quotes_service_request_id'), 'quotes', ['service_request_id'], unique=False)
    # 소프트삭제 미삭제 행만 중복 방지 — deleted_at IS NULL partial unique index
    op.create_index(
        'uq_quotes_request_pro', 'quotes',
        ['service_request_id', 'pro_id'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_quotes_request_pro', table_name='quotes')
    op.drop_index(op.f('ix_quotes_service_request_id'), table_name='quotes')
    op.drop_index(op.f('ix_quotes_pro_id'), table_name='quotes')
    op.drop_table('quotes')
    # drop_table은 PG enum 타입을 제거하지 않는다 → 재upgrade 시 "type already exists" 방지
    sa.Enum(name='quote_status').drop(op.get_bind(), checkfirst=True)
