"""Create base tables

Revision ID: 000
Revises: 
Create Date: 2024-08-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('telegram_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('age', sa.BigInteger(), nullable=True),
        sa.Column('gender', sa.String(), nullable=True),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('timezone', sa.String(), nullable=True),
        sa.Column('terms_accepted', sa.Boolean(), default=False),
        sa.Column('privacy_accepted', sa.Boolean(), default=False),
        sa.Column('policy_version', sa.String(), default='v1'),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('last_reminder_24h', sa.DateTime(), nullable=True),
        sa.Column('last_reminder_expiry', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'])
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=True)
    
    # Create subscriptions table
    op.create_table('subscriptions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('plan_name', sa.String(), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(), default='USD'),
        sa.Column('starts_at', sa.DateTime(), nullable=False),
        sa.Column('ends_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_trial', sa.Boolean(), default=False),
        sa.Column('payment_provider', sa.String(), nullable=True),
        sa.Column('payment_id', sa.String(), nullable=True),
        sa.Column('daily_messages_used', sa.BigInteger(), default=0),
        sa.Column('daily_messages_limit', sa.BigInteger(), default=5),
        sa.Column('daily_reset_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'])
    
    # Create conversations table  
    op.create_table('conversations',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_closed', sa.Boolean(), default=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('memory_context', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_id'), 'conversations', ['id'])
    op.create_index(op.f('ix_conversations_session_id'), 'conversations', ['session_id'])
    
    # Create messages table
    op.create_table('messages',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('is_crisis_related', sa.Boolean(), default=False),
        sa.Column('generated_blocks', sa.Integer(), default=1),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'])
    
    # Create bot_settings table
    op.create_table('bot_settings',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('string_value', sa.Text(), nullable=True),
        sa.Column('integer_value', sa.Integer(), nullable=True),
        sa.Column('boolean_value', sa.Boolean(), nullable=True),
        sa.Column('json_value', postgresql.JSON(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('changed_by', sa.String(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bot_settings_id'), 'bot_settings', ['id'])
    op.create_index(op.f('ix_bot_settings_key'), 'bot_settings', ['key'], unique=True)
    op.create_index(op.f('ix_bot_settings_category'), 'bot_settings', ['category'])
    
    # Create analytics_events table
    op.create_table('analytics_events',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('event_id', sa.String(), nullable=True),
        sa.Column('properties', postgresql.JSON(), nullable=True),
        sa.Column('message_length', sa.BigInteger(), nullable=True),
        sa.Column('token_count', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analytics_events_id'), 'analytics_events', ['id'])
    op.create_index(op.f('ix_analytics_events_event_type'), 'analytics_events', ['event_type'])
    op.create_index(op.f('ix_analytics_events_event_id'), 'analytics_events', ['event_id'])
    
    # Create user_sessions table
    op.create_table('user_sessions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('message_count', sa.BigInteger(), default=0),
        sa.Column('duration_minutes', sa.BigInteger(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('end_reason', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_sessions_id'), 'user_sessions', ['id'])
    op.create_index(op.f('ix_user_sessions_session_id'), 'user_sessions', ['session_id'])
    
    # Create memory_anchors table
    op.create_table('memory_anchors',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('anchor_id', sa.String(), nullable=False),
        sa.Column('topic', sa.String(), nullable=False),
        sa.Column('insight', sa.Text(), nullable=False),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('strength', sa.Integer(), default=1),
        sa.Column('last_referenced', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('auto_generated', sa.Boolean(), default=True),
        sa.Column('source_session_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memory_anchors_id'), 'memory_anchors', ['id'])
    op.create_index(op.f('ix_memory_anchors_anchor_id'), 'memory_anchors', ['anchor_id'])
    
    # Create conversation_summaries table
    op.create_table('conversation_summaries',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('main_topics', postgresql.JSON(), nullable=True),
        sa.Column('emotional_state', sa.String(), nullable=True),
        sa.Column('key_outcomes', postgresql.JSON(), nullable=True),
        sa.Column('message_count', sa.Integer(), default=0),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversation_summaries_id'), 'conversation_summaries', ['id'])
    
    # Create prompt_history table
    op.create_table('prompt_history',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('prompt_type', sa.String(50), nullable=False, default='system_prompt'),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('changed_by', sa.String(100), nullable=True),
        sa.Column('changed_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('is_active', sa.String(10), nullable=False, default='inactive'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prompt_history_id'), 'prompt_history', ['id'])
    op.create_index(op.f('ix_prompt_history_prompt_type'), 'prompt_history', ['prompt_type'])
    op.create_index(op.f('ix_prompt_history_is_active'), 'prompt_history', ['is_active'])


def downgrade():
    op.drop_index(op.f('ix_prompt_history_is_active'), table_name='prompt_history')
    op.drop_index(op.f('ix_prompt_history_prompt_type'), table_name='prompt_history')
    op.drop_index(op.f('ix_prompt_history_id'), table_name='prompt_history')
    op.drop_table('prompt_history')
    
    op.drop_index(op.f('ix_conversation_summaries_id'), table_name='conversation_summaries')
    op.drop_table('conversation_summaries')
    
    op.drop_index(op.f('ix_memory_anchors_anchor_id'), table_name='memory_anchors')
    op.drop_index(op.f('ix_memory_anchors_id'), table_name='memory_anchors')
    op.drop_table('memory_anchors')
    
    op.drop_index(op.f('ix_user_sessions_session_id'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_id'), table_name='user_sessions')
    op.drop_table('user_sessions')
    
    op.drop_index(op.f('ix_analytics_events_event_id'), table_name='analytics_events')
    op.drop_index(op.f('ix_analytics_events_event_type'), table_name='analytics_events')
    op.drop_index(op.f('ix_analytics_events_id'), table_name='analytics_events')
    op.drop_table('analytics_events')
    
    op.drop_index(op.f('ix_bot_settings_category'), table_name='bot_settings')
    op.drop_index(op.f('ix_bot_settings_key'), table_name='bot_settings')
    op.drop_index(op.f('ix_bot_settings_id'), table_name='bot_settings')
    op.drop_table('bot_settings')
    
    op.drop_index(op.f('ix_messages_id'), table_name='messages')
    op.drop_table('messages')
    
    op.drop_index(op.f('ix_conversations_session_id'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_id'), table_name='conversations')
    op.drop_table('conversations')
    
    op.drop_index(op.f('ix_subscriptions_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    
    op.drop_index(op.f('ix_users_telegram_id'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')