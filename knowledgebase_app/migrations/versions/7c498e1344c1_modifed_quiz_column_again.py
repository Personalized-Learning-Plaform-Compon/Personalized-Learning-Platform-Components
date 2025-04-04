"""modifed quiz column again

Revision ID: 7c498e1344c1
Revises: 2ba9a8d64748
Create Date: 2025-04-02 23:35:32.732159

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c498e1344c1'
down_revision = '2ba9a8d64748'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.alter_column('content',
               existing_type=sa.TEXT(),
               type_=sa.JSON(),
               postgresql_using='content::json',
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.alter_column('content',
               existing_type=sa.JSON(),
               type_=sa.TEXT(),
               existing_nullable=False)

    # ### end Alembic commands ###
