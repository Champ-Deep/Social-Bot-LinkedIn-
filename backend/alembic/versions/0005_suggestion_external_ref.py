"""Add outreach_suggestions.external_ref (unique, nullable) for Harbinger handoffs.

Guarded by an inspector check for the same reason as 0004: a database built from
the current models (AUTO_CREATE_TABLES) already has the column and index.

Revision ID: 0005
Revises: 0004
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "outreach_suggestions"
INDEX = "ix_outreach_suggestions_external_ref"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "external_ref" not in {c["name"] for c in inspector.get_columns(TABLE)}:
        with op.batch_alter_table(TABLE, schema=None) as batch_op:
            batch_op.add_column(sa.Column("external_ref", sa.String(length=128), nullable=True))
    if INDEX not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(TABLE)}:
        op.create_index(INDEX, TABLE, ["external_ref"], unique=True)


def downgrade() -> None:
    op.drop_index(INDEX, table_name=TABLE)
    with op.batch_alter_table(TABLE, schema=None) as batch_op:
        batch_op.drop_column("external_ref")
