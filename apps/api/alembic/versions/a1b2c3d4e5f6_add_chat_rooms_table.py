"""add_chat_rooms_table

Revision ID: a1b2c3d4e5f6
Revises: d7bffeb07473
Create Date: 2026-06-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd7bffeb07473'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'chat_rooms',
        sa.Column('service_request_id', sa.UUID(), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('pro_id', sa.UUID(), nullable=False),
        sa.Column('quote_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pro_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id']),
        sa.ForeignKeyConstraint(['service_request_id'], ['service_requests.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quote_id'),
    )
    op.create_index(op.f('ix_chat_rooms_customer_id'), 'chat_rooms', ['customer_id'], unique=False)
    op.create_index(op.f('ix_chat_rooms_pro_id'), 'chat_rooms', ['pro_id'], unique=False)
    op.create_index(op.f('ix_chat_rooms_service_request_id'), 'chat_rooms', ['service_request_id'], unique=False)

    # 요청당 accepted 견적 하나만 허용 — race condition 차단 partial unique index (AR7)
    op.create_index(
        'uq_quotes_accepted_per_request',
        'quotes',
        ['service_request_id'],
        unique=True,
        postgresql_where=sa.text("status = 'accepted' AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_quotes_accepted_per_request', table_name='quotes')
    op.drop_index(op.f('ix_chat_rooms_service_request_id'), table_name='chat_rooms')
    op.drop_index(op.f('ix_chat_rooms_pro_id'), table_name='chat_rooms')
    op.drop_index(op.f('ix_chat_rooms_customer_id'), table_name='chat_rooms')
    op.drop_table('chat_rooms')
