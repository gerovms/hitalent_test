"""init

Revision ID: 0001_init
Revises: 
Create Date: 2026-02-20

"""

from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_departments_parent_id", "departments", ["parent_id"])
    # Уникальность имени в пределах parent, включая parent_id IS NULL:
    op.create_index(
        "uq_departments_parent_name",
        "departments",
        [sa.text("coalesce(parent_id, 0)"), "name"],
        unique=True,
        postgresql_using="btree",
    )

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("position", sa.String(length=200), nullable=False),
        sa.Column("hired_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_employees_department_id", "employees", ["department_id"])


def downgrade() -> None:
    op.drop_index("ix_employees_department_id", table_name="employees")
    op.drop_table("employees")

    op.drop_index("uq_departments_parent_name", table_name="departments")
    op.drop_index("ix_departments_parent_id", table_name="departments")
    op.drop_table("departments")
