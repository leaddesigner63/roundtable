"""Use BigInteger for telegram id

Revision ID: 81772eb4e4d1
Revises: 0001_initial
Create Date: 2025-10-02 06:58:03.644462

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '81772eb4e4d1'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "telegram_id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )

    with op.batch_alter_table("sessions", schema=None) as batch_op:
        if dialect != "sqlite":
            batch_op.drop_constraint("sessions_user_id_fkey", type_="foreignkey")

        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )

        if dialect != "sqlite":
            batch_op.create_foreign_key(
                "sessions_user_id_fkey",
                "users",
                ["user_id"],
                ["telegram_id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    with op.batch_alter_table("sessions", schema=None) as batch_op:
        if dialect != "sqlite":
            batch_op.drop_constraint("sessions_user_id_fkey", type_="foreignkey")

        batch_op.alter_column(
            "user_id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )

        if dialect != "sqlite":
            batch_op.create_foreign_key(
                "sessions_user_id_fkey",
                "users",
                ["user_id"],
                ["telegram_id"],
            )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "telegram_id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )
