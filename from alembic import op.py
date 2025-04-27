from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('email', sa.String(), unique=True, nullable=False),
        sa.Column('username', sa.String(), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('rate_limit', sa.Integer(), default=100)
    )
    
    op.create_table(
        'analysis_results',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id')),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('score', sa.Float()),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('metadata', sa.JSON())
    )

def downgrade():
    op.drop_table('analysis_results')
    op.drop_table('users')
