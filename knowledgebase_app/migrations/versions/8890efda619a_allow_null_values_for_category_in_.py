"""Allow NULL values for category in course_content

Revision ID: 8890efda619a
Revises: c0ddd74ce87d
Create Date: 2025-02-19 19:57:58.803643

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8890efda619a'
down_revision = 'c0ddd74ce87d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('course_content', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category', sa.String(length=255), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('course_content', schema=None) as batch_op:
        batch_op.drop_column('category')

    # ### end Alembic commands ###
