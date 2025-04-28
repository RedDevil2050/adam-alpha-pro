"""Initial database schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-04-28 16:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('username', sa.String(100), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('is_superuser', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # API Keys for users
    op.create_table(
        'api_keys',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key_name', sa.String(100), nullable=False),
        sa.Column('api_key', sa.String(255), nullable=False),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True)
    )
    op.create_index(op.f('ix_api_keys_user_id'), 'api_keys', ['user_id'])
    op.create_index(op.f('ix_api_keys_provider'), 'api_keys', ['provider'])
    
    # Portfolios
    op.create_table(
        'portfolios',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    op.create_index(op.f('ix_portfolios_user_id'), 'portfolios', ['user_id'])
    
    # Portfolio positions
    op.create_table(
        'portfolio_positions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('portfolio_id', UUID(as_uuid=True), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=True),
        sa.Column('entry_date', sa.DateTime(), nullable=True),
        sa.Column('current_price', sa.Float(), nullable=True),
        sa.Column('last_price_update', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    op.create_index(op.f('ix_portfolio_positions_portfolio_id'), 'portfolio_positions', ['portfolio_id'])
    op.create_index(op.f('ix_portfolio_positions_symbol'), 'portfolio_positions', ['symbol'])
    
    # Watchlists
    op.create_table(
        'watchlists',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    op.create_index(op.f('ix_watchlists_user_id'), 'watchlists', ['user_id'])
    
    # Watchlist items
    op.create_table(
        'watchlist_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('watchlist_id', UUID(as_uuid=True), sa.ForeignKey('watchlists.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('added_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index(op.f('ix_watchlist_items_watchlist_id'), 'watchlist_items', ['watchlist_id'])
    op.create_index(op.f('ix_watchlist_items_symbol'), 'watchlist_items', ['symbol'])
    
    # Alerts
    op.create_table(
        'alerts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),  # price, technical, news, etc.
        sa.Column('condition', sa.String(255), nullable=False),  # e.g., "price > 100"
        sa.Column('parameters', JSONB, nullable=True),  # Additional parameters
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_triggered', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    op.create_index(op.f('ix_alerts_user_id'), 'alerts', ['user_id'])
    op.create_index(op.f('ix_alerts_symbol'), 'alerts', ['symbol'])
    op.create_index(op.f('ix_alerts_alert_type'), 'alerts', ['alert_type'])
    
    # Analysis results
    op.create_table(
        'analysis_results',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('agent_name', sa.String(100), nullable=False),
        sa.Column('agent_type', sa.String(100), nullable=False),
        sa.Column('result_data', JSONB, nullable=False),
        sa.Column('parameters', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=True)
    )
    op.create_index(op.f('ix_analysis_results_symbol'), 'analysis_results', ['symbol'])
    op.create_index(op.f('ix_analysis_results_agent_name'), 'analysis_results', ['agent_name'])
    op.create_index(op.f('ix_analysis_results_agent_type'), 'analysis_results', ['agent_type'])
    op.create_index(op.f('ix_analysis_results_created_at'), 'analysis_results', ['created_at'])


def downgrade() -> None:
    op.drop_table('analysis_results')
    op.drop_table('alerts')
    op.drop_table('watchlist_items')
    op.drop_table('watchlists')
    op.drop_table('portfolio_positions')
    op.drop_table('portfolios')
    op.drop_table('api_keys')
    op.drop_table('users')