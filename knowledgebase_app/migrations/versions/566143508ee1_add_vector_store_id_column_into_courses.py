"""Add vector_store_id column into courses

Revision ID: 566143508ee1
Revises: 47d6ef7088c1
Create Date: 2025-03-12 17:31:17.447386

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '566143508ee1'
down_revision = '47d6ef7088c1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vector_store_id', sa.String(length=255), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.drop_column('vector_store_id')

    # ### end Alembic commands ###
