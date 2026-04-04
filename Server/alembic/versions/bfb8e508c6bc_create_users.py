"""Create Users

Revision ID: bfb8e508c6bc
Revises: 
Create Date: 2026-04-04 15:18:59.664144

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'bfb8e508c6bc'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("phone", sa.String(20)),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    
    op.create_table("stocks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(20), nullable=False, unique=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("exchange", sa.String(10), server_default="NSE"),
        sa.Column("sector", sa.String(100)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )

    op.create_table("predictions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("stock_id", sa.Integer(), sa.ForeignKey("stocks.id"), nullable=False),
        sa.Column("prediction_date", sa.Date(), nullable=False),
        sa.Column("signal", sa.String(10), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("close_price", sa.Float(), nullable=False),
        sa.Column("limit_price_suggested", sa.Float()),
        sa.Column("target_low", sa.Float()),
        sa.Column("target_high", sa.Float()),
        sa.Column("reasoning", sa.Text()),
        sa.Column("factors", JSONB()),
        sa.Column("model_used", sa.String(50)),
        sa.Column("generated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table("outcomes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("prediction_id", sa.Integer(), sa.ForeignKey("predictions.id"), nullable=False, unique=True),
        sa.Column("actual_open", sa.Float()),
        sa.Column("actual_close", sa.Float()),
        sa.Column("direction_correct", sa.Boolean()),
        sa.Column("pnl_pct", sa.Float()),
        sa.Column("recorded_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table("user_saved_predictions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("prediction_id", sa.Integer(), sa.ForeignKey("predictions.id"), nullable=False),
        sa.Column("saved_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table("market_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("stock_id", sa.Integer(), sa.ForeignKey("stocks.id"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float()),
        sa.Column("high", sa.Float()),
        sa.Column("low", sa.Float()),
        sa.Column("close", sa.Float()),
        sa.Column("volume", sa.BigInteger()),
        sa.Column("rsi", sa.Float()),
        sa.Column("macd", sa.Float()),
        sa.Column("macd_signal", sa.Float()),
        sa.Column("raw_data", JSONB()),
        sa.Column("fetched_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table("news_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("stock_id", sa.Integer(), sa.ForeignKey("stocks.id"), nullable=False),
        sa.Column("news_date", sa.Date(), nullable=False),
        sa.Column("headline", sa.String(500), nullable=False),
        sa.Column("source", sa.String(100)),
        sa.Column("url", sa.String(1000)),
        sa.Column("sentiment", sa.String(10)),
        sa.Column("sentiment_score", sa.Float()),
        sa.Column("published_at", sa.DateTime()),
    )


def downgrade():
    op.drop_table("user_saved_predictions")
    op.drop_table("news_items")
    op.drop_table("stocks")
    op.drop_table("market_snapshots")
    op.drop_table("outcomes")
    op.drop_table("predictions")
    op.drop_table("users")