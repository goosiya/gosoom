"""add_messages_table

Revision ID: 217b0b5d93d4
Revises: a1b2c3d4e5f6
Create Date: 2026-06-11 08:06:24.420207

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '217b0b5d93d4'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('chat_room_id', sa.UUID(), nullable=False),
        sa.Column('sender_id', sa.UUID(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['chat_room_id'], ['chat_rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_messages_chat_room_id', 'messages', ['chat_room_id'])
    op.create_index('ix_messages_chat_room_id_id', 'messages', ['chat_room_id', 'id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_messages_chat_room_id_id', table_name='messages')
    op.drop_index('ix_messages_chat_room_id', table_name='messages')
    op.drop_table('messages')
