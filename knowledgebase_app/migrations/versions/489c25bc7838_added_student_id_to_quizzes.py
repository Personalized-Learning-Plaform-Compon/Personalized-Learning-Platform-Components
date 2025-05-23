"""added student id to quizzes

Revision ID: 489c25bc7838
Revises: 7c498e1344c1
Create Date: 2025-04-02 23:43:52.187892

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '489c25bc7838'
down_revision = '7c498e1344c1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('student_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key(None, 'students', ['student_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('student_id')

    # ### end Alembic commands ###
