"""Lead capture fields on company.

Adds lead_capture_enabled toggle and lead_capture_consent_text to companies.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202611220007"
down_revision: Union[str, None] = "202611220006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("lead_capture_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "companies",
        sa.Column(
            "lead_capture_consent_text",
            sa.Text(),
            nullable=False,
            server_default="قد نطلب بعض التفاصيل (مثل الاسم أو رقم الهاتف) لتحسين الخدمة. يمكنك رفض مشاركة أي بيانات لا تريد الكشف عنها.",
        ),
    )


def downgrade() -> None:
    op.drop_column("companies", "lead_capture_consent_text")
    op.drop_column("companies", "lead_capture_enabled")
